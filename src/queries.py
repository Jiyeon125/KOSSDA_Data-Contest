"""SQLite DB 조회 모듈.

data/db/youth_analysis.sqlite3 에 대해 SQL 쿼리를 실행하고
결과를 pandas DataFrame 으로 반환하는 함수들을 제공한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "db" / "youth_analysis.sqlite3"


def run_query(
    sql: str,
    params: tuple | dict | None = None,
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """SQL 쿼리를 실행해 결과를 DataFrame 으로 반환한다.

    Args:
        sql: 실행할 SQL 문자열.
        params: 파라미터 바인딩에 사용할 값 (선택).
        db_path: 사용할 SQLite 파일 경로.

    Returns:
        쿼리 결과 DataFrame.

    Raises:
        FileNotFoundError: DB 파일이 아직 생성되지 않았을 때.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"[queries] DB 파일이 없습니다: {db_path}\n"
            "          먼저 `python -m src.build_db` 로 DB 를 생성하세요."
        )

    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def list_tables(db_path: Path = DB_PATH) -> pd.DataFrame:
    """DB 에 존재하는 테이블 목록을 DataFrame 으로 반환한다."""
    sql = "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;"
    return run_query(sql, db_path=db_path)


def preview_table(table_name: str, limit: int = 10, db_path: Path = DB_PATH) -> pd.DataFrame:
    """특정 테이블의 상위 N개 행을 미리 본다.

    Args:
        table_name: 조회할 테이블 이름.
        limit: 가져올 행 수 (기본 10).
        db_path: 사용할 SQLite 파일 경로.
    """
    # 테이블명은 바인딩이 불가능하므로 식별자만 안전하게 따옴표 처리한다.
    safe_name = table_name.replace('"', '""')
    sql = f'SELECT * FROM "{safe_name}" LIMIT ?;'
    return run_query(sql, params=(limit,), db_path=db_path)


if __name__ == "__main__":
    try:
        print(list_tables())
    except FileNotFoundError as exc:
        print(exc)
