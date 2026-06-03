"""SQLite DB 조회 모듈.

data/db/youth_analysis.sqlite3 에 연결해 SQL 쿼리를 실행하고
결과를 pandas DataFrame 으로 반환한다. 테이블/컬럼 목록 조회 함수도 제공한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
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


# ----------------------------------------------------------------------
# 가중 추정 헬퍼 (가중=모집단 대표 비율/규모, 검정 n 은 비가중 사용)
#   weight_person: 응답자 1명이 대표하는 모집단 인원 수
# ----------------------------------------------------------------------
WEIGHT_COL = "weight_person"


def weighted_share(
    df: pd.DataFrame,
    flag_col: str,
    weight_col: str = WEIGHT_COL,
) -> dict:
    """이항 플래그(0/1)의 가중 비율(%)과 모집단 추정 규모(명)를 계산한다."""
    f = pd.to_numeric(df[flag_col], errors="coerce")
    w = pd.to_numeric(df[weight_col], errors="coerce")
    mask = f.notna() & w.notna()
    f, w = f[mask], w[mask]
    if w.sum() == 0:
        return {"비율_가중(%)": None, "비율_비가중(%)": None, "모집단추정(명)": 0, "표본n": 0}
    return {
        "비율_가중(%)": round(float((w[f == 1].sum()) / w.sum() * 100), 1),
        "비율_비가중(%)": round(float((f == 1).mean() * 100), 1),
        "모집단추정(명)": int(round(float(w[f == 1].sum()))),
        "표본n": int((f == 1).sum()),
    }


def weighted_mean(
    df: pd.DataFrame,
    value_col: str,
    weight_col: str = WEIGHT_COL,
) -> float | None:
    """수치형 변수의 가중 평균."""
    v = pd.to_numeric(df[value_col], errors="coerce")
    w = pd.to_numeric(df[weight_col], errors="coerce")
    mask = v.notna() & w.notna()
    v, w = v[mask], w[mask]
    if w.sum() == 0:
        return None
    return round(float((v * w).sum() / w.sum()), 2)


def weighted_group_share(
    df: pd.DataFrame,
    group_col: str,
    weight_col: str = WEIGHT_COL,
) -> pd.DataFrame:
    """범주형 그룹별 가중 비율(%)·모집단 추정 규모·표본수를 반환한다."""
    w = pd.to_numeric(df[weight_col], errors="coerce")
    sub = df[[group_col]].copy()
    sub["_w"] = w
    sub = sub.dropna(subset=[group_col, "_w"])
    total_w = sub["_w"].sum()
    rows = []
    for g, gdf in sub.groupby(group_col):
        rows.append({
            "집단": g,
            "표본n": int(len(gdf)),
            "비율_가중(%)": round(float(gdf["_w"].sum() / total_w * 100), 1) if total_w else None,
            "비율_비가중(%)": round(float(len(gdf) / len(sub) * 100), 1),
            "모집단추정(명)": int(round(float(gdf["_w"].sum()))),
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 통계 검정 헬퍼 (공모전: 유의성·효과크기 보고용)
#   - 비모수 검정(Mann-Whitney U)으로 두 집단의 연속형 변수 비교
#   - 카이제곱 검정으로 두 집단의 비율(이항 플래그) 비교
#   - 효과크기(rank-biserial / Cramér's V)와 표본수를 함께 보고
# ----------------------------------------------------------------------
ANALYSIS_TABLE = "youth_life_2024_analysis"


def _effect_label_r(r: float) -> str:
    """효과크기 |r| 해석 라벨(Cohen 관행)."""
    a = abs(r)
    if a < 0.1:
        return "무시할 수준"
    if a < 0.3:
        return "작음"
    if a < 0.5:
        return "중간"
    return "큼"


def mann_whitney_compare(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    group_a,
    group_b,
) -> dict:
    """두 집단의 연속형 변수 차이를 Mann-Whitney U 로 검정한다.

    효과크기는 rank-biserial correlation(=1-2U/(n1·n2))로 보고한다.
    """
    from scipy import stats  # 지연 import (앱 시작 비용 절감)

    a = pd.to_numeric(df.loc[df[group_col] == group_a, value_col], errors="coerce").dropna()
    b = pd.to_numeric(df.loc[df[group_col] == group_b, value_col], errors="coerce").dropna()
    res: dict = {
        "변수": value_col,
        "집단A": str(group_a),
        "집단B": str(group_b),
        "n_A": int(a.size),
        "n_B": int(b.size),
        "중앙값_A": round(float(a.median()), 1) if not a.empty else None,
        "중앙값_B": round(float(b.median()), 1) if not b.empty else None,
        "평균_A": round(float(a.mean()), 1) if not a.empty else None,
        "평균_B": round(float(b.mean()), 1) if not b.empty else None,
    }
    if a.size < 2 or b.size < 2:
        res.update({"U": None, "p": None, "효과크기r": None, "효과해석": "표본부족", "유의": ""})
        return res

    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    r_rb = 1.0 - (2.0 * u) / (a.size * b.size)
    res.update({
        "U": round(float(u), 1),
        "p": float(p),
        "효과크기r": round(float(r_rb), 3),
        "효과해석": _effect_label_r(r_rb),
        "유의": "유의(p<.05)" if p < 0.05 else "비유의",
    })
    return res


def chi_square_compare(
    df: pd.DataFrame,
    group_col: str,
    flag_col: str,
    group_a,
    group_b,
) -> dict:
    """두 집단의 이항 플래그(0/1) 비율 차이를 카이제곱으로 검정한다.

    효과크기는 2x2 Cramér's V(=phi)로 보고한다. 기대빈도가 작으면 경고한다.
    """
    from scipy import stats

    sub = df[df[group_col].isin([group_a, group_b])][[group_col, flag_col]].copy()
    sub[flag_col] = pd.to_numeric(sub[flag_col], errors="coerce")
    sub = sub.dropna()
    res: dict = {"변수": flag_col, "집단A": str(group_a), "집단B": str(group_b)}
    if sub.empty:
        res.update({"비율A(%)": None, "비율B(%)": None, "p": None, "효과크기V": None, "유의": "표본부족"})
        return res

    a = sub.loc[sub[group_col] == group_a, flag_col]
    b = sub.loc[sub[group_col] == group_b, flag_col]
    res["n_A"], res["n_B"] = int(a.size), int(b.size)
    res["비율A(%)"] = round(float(a.mean() * 100), 1) if a.size else None
    res["비율B(%)"] = round(float(b.mean() * 100), 1) if b.size else None

    ct = pd.crosstab(sub[group_col], sub[flag_col])
    if ct.shape != (2, 2):
        res.update({"p": None, "효과크기V": None, "유의": "2x2 아님"})
        return res

    chi2, p, _, expected = stats.chi2_contingency(ct, correction=True)
    n = ct.values.sum()
    v = float(np.sqrt(chi2 / n)) if n else 0.0
    res.update({
        "p": float(p),
        "효과크기V": round(v, 3),
        "효과해석": _effect_label_r(v),
        "최소기대빈도": round(float(expected.min()), 1),
        "유의": "유의(p<.05)" if p < 0.05 else "비유의",
    })
    if expected.min() < 5:
        res["경고"] = "기대빈도<5 (해석 주의)"
    return res


if __name__ == "__main__":
    try:
        tables = list_tables()
        print("[queries] 테이블 목록:", tables)
        for t in tables:
            print(f"  - {t}: {list_columns(t)}")
    except FileNotFoundError as exc:
        print(exc)
