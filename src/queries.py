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


if __name__ == "__main__":
    try:
        tables = list_tables()
        print("[queries] 테이블 목록:", tables)
        for t in tables:
            print(f"  - {t}: {list_columns(t)}")
    except FileNotFoundError as exc:
        print(exc)
