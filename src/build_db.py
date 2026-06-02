"""CSV 파일을 읽어 SQLite DB 로 적재하는 모듈.

data/raw 의 CSV 파일을 읽어 pandas DataFrame 으로 변환한 뒤,
data/db/youth_analysis.sqlite3 에 테이블로 저장한다.

실행 예시:
    python -m src.build_db
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_DIR = PROJECT_ROOT / "data" / "db"
DB_PATH = DB_DIR / "youth_analysis.sqlite3"


def csv_to_sqlite(
    csv_filename: str,
    table_name: str,
    db_path: Path = DB_PATH,
    if_exists: str = "replace",
) -> bool:
    """data/raw 의 CSV 파일을 읽어 SQLite 테이블로 저장한다.

    Args:
        csv_filename: data/raw 안의 CSV 파일명 (예: "youth.csv").
        table_name: 저장할 SQLite 테이블 이름.
        db_path: 생성/사용할 SQLite 파일 경로. 기본값은 youth_analysis.sqlite3.
        if_exists: 테이블이 이미 있을 때 동작 ("replace" | "append" | "fail").

    Returns:
        저장 성공 시 True, 파일이 없거나 실패 시 False.
    """
    csv_path = RAW_DIR / csv_filename

    # 파일이 없을 때 에러 메시지 출력 후 종료
    if not csv_path.exists():
        print(f"[build_db] 오류: CSV 파일을 찾을 수 없습니다 -> {csv_path}")
        print("          data/raw 폴더에 파일을 넣은 뒤 다시 실행하세요.")
        return False

    # DB 폴더가 없으면 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여준다
        print(f"[build_db] 오류: CSV 읽기 실패 ({csv_path}) -> {exc}")
        return False

    # pandas DataFrame 을 SQLite 테이블로 저장
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)

    print(
        f"[build_db] 저장 완료: '{table_name}' 테이블 "
        f"({len(df):,} 행) -> {db_path}"
    )
    return True


def build_all() -> None:
    """data/raw 의 모든 CSV 파일을 파일명 기반 테이블로 일괄 적재한다.

    예) data/raw/youth.csv -> 'youth' 테이블
    """
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"[build_db] data/raw 에 CSV 파일이 없습니다: {RAW_DIR}")
        print("          (실제 데이터를 넣은 뒤 다시 실행하세요.)")
        return

    for csv_path in csv_files:
        table_name = csv_path.stem  # 확장자를 제외한 파일명
        csv_to_sqlite(csv_path.name, table_name)


if __name__ == "__main__":
    build_all()
