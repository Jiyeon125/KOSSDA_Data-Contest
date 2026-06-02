"""SQLite DB 조회 모듈.

data/db/youth_analysis.sqlite3 에 연결해 SQL 쿼리를 실행하고
결과를 pandas DataFrame 으로 반환한다. 테이블/컬럼 목록 조회 함수도 제공한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로 (Windows 호환을 위해 pathlib 사용)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "db" / "youth_analysis.sqlite3"


def db_exists(db_path: Path = DB_PATH) -> bool:
    """DB 파일이 존재하는지 확인한다."""
    return Path(db_path).exists()


def run_query(
    sql: str,
    params: tuple | dict | None = None,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """SQL 쿼리를 실행해 결과를 DataFrame 으로 반환한다.

    Args:
        sql: 실행할 SQL 문자열.
        params: 파라미터 바인딩 값 (선택).
        db_path: 사용할 SQLite 파일 경로.

    Raises:
        FileNotFoundError: DB 파일이 아직 없을 때.
    """
    if not db_exists(db_path):
        raise FileNotFoundError(
            f"[queries] DB 파일이 없습니다: {db_path}\n"
            "          먼저 `python src/build_db.py` 로 DB 를 생성하세요."
        )

    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def list_tables(db_path: Path = DB_PATH) -> list[str]:
    """DB 에 존재하는 테이블 이름 목록을 반환한다."""
    sql = (
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name;"
    )
    df = run_query(sql, db_path=db_path)
    return df["name"].tolist()


def list_columns(table_name: str, db_path: Path = DB_PATH) -> list[str]:
    """특정 테이블의 컬럼 이름 목록을 반환한다.

    PRAGMA table_info 를 사용하므로 SQL 인젝션 방지를 위해
    테이블명은 식별자 따옴표로 감싼다.
    """
    safe_name = str(table_name).replace('"', '""')
    sql = f'PRAGMA table_info("{safe_name}");'
    df = run_query(sql, db_path=db_path)
    if df.empty:
        return []
    return df["name"].tolist()


def preview_table(
    table_name: str,
    limit: int = 10,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """특정 테이블의 상위 N개 행을 미리 본다."""
    safe_name = str(table_name).replace('"', '""')
    sql = f'SELECT * FROM "{safe_name}" LIMIT ?;'
    return run_query(sql, params=(limit,), db_path=db_path)


# ----------------------------------------------------------------------
# 청년삶 2024 분석용 테이블/헬퍼
# ----------------------------------------------------------------------
YOUTH_ALL_TABLE = "youth_life_youth_2024_all"
YOUTH_RESTED_TABLE = "youth_life_youth_2024_rested"


def _fetch_columns(table_name: str, columns: list[str], db_path: Path = DB_PATH) -> pd.DataFrame:
    """테이블에서 지정한 컬럼만 조회한다."""
    safe_table = str(table_name).replace('"', '""')
    cols_sql = ", ".join(f'"{c}"' for c in columns)
    return run_query(f'SELECT {cols_sql} FROM "{safe_table}";', db_path=db_path)


def numeric_summary(
    table_name: str,
    columns: list[str],
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """수치형 컬럼들의 기술통계를 계산한다.

    각 컬럼별로 평균/중앙값/Q1/Q3/0 비율/양수자 평균/표본수를 반환한다.
    (분석 1: 쉬었음 청년 기술통계)
    """
    df = _fetch_columns(table_name, columns, db_path=db_path)
    rows = []
    for col in columns:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        positive = s[s > 0]
        rows.append(
            {
                "변수": col,
                "n": int(s.size),
                "평균": round(float(s.mean()), 1),
                "중앙값": round(float(s.median()), 1),
                "Q1": round(float(s.quantile(0.25)), 1),
                "Q3": round(float(s.quantile(0.75)), 1),
                "0_비율(%)": round(float((s == 0).mean() * 100), 1),
                "양수자_평균": round(float(positive.mean()), 1) if not positive.empty else 0.0,
            }
        )
    return pd.DataFrame(rows)


def help_network_share(
    table_name: str,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """생활비 부족 시 도움 가능 집단의 응답 비율(%)을 계산한다.

    (분석 2: 생활비 지원망)
    """
    help_cols = {
        "help_family": "가족",
        "help_acquaintance": "지인",
        "help_public": "공공기관",
        "help_private": "민간기관",
        "help_none": "없음",
    }
    df = _fetch_columns(table_name, list(help_cols), db_path=db_path)
    rows = []
    for col, label in help_cols.items():
        s = pd.to_numeric(df[col], errors="coerce")
        rows.append({"집단": label, "비율(%)": round(float((s == 1).mean() * 100), 1)})
    return pd.DataFrame(rows)


def group_means(
    table_name: str,
    group_col: str,
    value_cols: list[str],
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """그룹별 평균을 계산한다 (분석 3·4: 부모동거 / 도움유무 비교)."""
    df = _fetch_columns(table_name, [group_col] + value_cols, db_path=db_path)
    for c in value_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    agg = df.groupby(group_col)[value_cols].mean().round(1).reset_index()
    return agg


if __name__ == "__main__":
    try:
        tables = list_tables()
        print("[queries] 테이블 목록:", tables)
        for t in tables:
            print(f"  - {t}: {list_columns(t)}")
    except FileNotFoundError as exc:
        print(exc)
