"""전처리된 CSV 파일을 SQLite DB 로 적재하는 모듈.

data/processed 폴더의 CSV 파일들을 읽어
data/db/youth_analysis.sqlite3 에 테이블로 저장한다.
테이블명은 파일명에서 확장자를 제거한 이름을 사용한다.

실행 방법:
    python src/build_db.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로 (Windows 호환을 위해 pathlib 사용)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_DIR = PROJECT_ROOT / "data" / "db"
DB_PATH = DB_DIR / "youth_analysis.sqlite3"


def _read_csv_flexible(csv_path: Path) -> pd.DataFrame:
    """전처리 CSV 를 읽는다. utf-8 계열 -> cp949 순으로 시도한다."""
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 마지막 시도 (오류를 그대로 표면화)
    return pd.read_csv(csv_path)


def load_processed_to_db(db_path: Path = DB_PATH, if_exists: str = "replace") -> int:
    """data/processed 의 모든 CSV 를 SQLite DB 테이블로 저장한다.

    Args:
        db_path: 생성/사용할 SQLite 파일 경로.
        if_exists: 테이블이 이미 있을 때 동작 ("replace" | "append" | "fail").

    Returns:
        성공적으로 저장한 테이블 개수.
    """
    if not PROCESSED_DIR.exists():
        print(f"[build_db] 오류: 폴더가 없습니다 -> {PROCESSED_DIR}")
        print("          먼저 전처리를 수행해 data/processed 에 CSV 를 만드세요.")
        return 0

    csv_files = sorted(PROCESSED_DIR.glob("*.csv"))
    if not csv_files:
        print(f"[build_db] data/processed 에 CSV 파일이 없습니다: {PROCESSED_DIR}")
        print("          먼저 `python src/preprocess.py` 로 전처리 결과를 만드세요.")
        return 0

    # DB 폴더가 없으면 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    with sqlite3.connect(db_path) as conn:
        for csv_path in csv_files:
            table_name = csv_path.stem  # 확장자를 제외한 파일명
            try:
                df = _read_csv_flexible(csv_path)
            except Exception as exc:  # noqa: BLE001 - 원인을 사용자에게 표시
                print(f"[build_db] 건너뜀: '{csv_path.name}' 읽기 실패 -> {exc}")
                continue

            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            print(f"[build_db] 저장 완료: 테이블 '{table_name}' <- {csv_path.name} ({len(df):,} 행)")
            saved_count += 1

    if saved_count:
        print(f"[build_db] 총 {saved_count}개 테이블 저장 -> {db_path}")
    return saved_count


if __name__ == "__main__":
    load_processed_to_db()
