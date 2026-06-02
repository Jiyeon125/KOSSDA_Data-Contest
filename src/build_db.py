"""전처리된 CSV 파일을 SQLite DB 로 적재하는 모듈.

data/processed 폴더의 CSV 파일들을 읽어
data/db/youth_analysis.sqlite3 에 테이블로 저장한다.
테이블명은 파일명에서 확장자를 제거한 이름을 사용한다.

데이터 규모가 커질 수 있으므로 모든 파일을 무작정 적재하지 않고,
인자로 특정 파일만 선택해 적재할 수 있다. 코드북 파일은 자동 제외한다.

실행 방법:
    # data/processed(하위 폴더 포함)의 모든 CSV 적재 (코드북 제외)
    python src/build_db.py

    # 특정 파일만 선택해 적재 ((상대)경로 또는 파일명)
    python src/build_db.py youth_life/youth_2024_clean.csv eaps_clean.csv
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# 스크립트로 직접 실행할 때(python src/build_db.py)도 src 패키지를
# import 할 수 있도록 프로젝트 루트를 모듈 경로에 추가한다.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.preprocess import looks_like_codebook  # noqa: E402

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


def table_name_from(path: Path) -> str:
    """파일 경로에서 안전한 SQLite 테이블명을 만든다.

    하위 폴더로 정리된 경우 폴더명을 접두로 붙여 테이블명 충돌을 방지한다.
    예) processed/youth_life/youth_2024_clean.csv -> youth_life_youth_2024_clean
    """
    rel = path.relative_to(PROCESSED_DIR).with_suffix("")
    joined = "_".join(rel.parts)
    # 영문/숫자/언더스코어/한글 외 문자는 _ 로 치환
    name = re.sub(r"[^0-9A-Za-z_가-힣]", "_", joined)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "table"


def _select_target_files(only: list[str] | None) -> list[Path]:
    """적재할 CSV 파일 목록을 결정한다.

    - only 가 주어지면 해당 (상대)경로/파일명만 대상으로 한다.
    - only 가 없으면 data/processed(하위 폴더 포함)의 모든 CSV 를 대상으로 한다.
    - 코드북으로 보이는 파일은 항상 제외한다.
    """
    all_csv = sorted(PROCESSED_DIR.rglob("*.csv"))

    if only:
        selected: list[Path] = []
        for name in only:
            candidate = PROCESSED_DIR / name
            if candidate.exists() and candidate.is_file():
                selected.append(candidate)
                continue
            # 파일명만으로 매칭 시도
            matches = [p for p in all_csv if p.name == name]
            if len(matches) == 1:
                selected.append(matches[0])
            elif len(matches) > 1:
                print(f"[build_db] 같은 이름이 여러 개 있습니다. 상대경로로 지정하세요: {name}")
            else:
                print(f"[build_db] 건너뜀: 지정한 파일이 없습니다 -> {name}")
        files = selected
    else:
        files = all_csv

    # 코드북 파일은 DB 에 넣지 않는다 (변수 해석용 참고자료)
    kept: list[Path] = []
    for path in files:
        if looks_like_codebook(path.name):
            print(f"[build_db] 제외(코드북으로 판단): {path.relative_to(PROCESSED_DIR).as_posix()}")
            continue
        kept.append(path)
    return kept


def load_processed_to_db(
    db_path: Path = DB_PATH,
    if_exists: str = "replace",
    only: list[str] | None = None,
) -> int:
    """data/processed 의 CSV 를 SQLite DB 테이블로 저장한다.

    Args:
        db_path: 생성/사용할 SQLite 파일 경로.
        if_exists: 테이블이 이미 있을 때 동작 ("replace" | "append" | "fail").
        only: 적재할 파일명 목록. None 이면 (코드북 제외) 전체 CSV 를 적재한다.

    Returns:
        성공적으로 저장한 테이블 개수.
    """
    if not PROCESSED_DIR.exists():
        print(f"[build_db] 오류: 폴더가 없습니다 -> {PROCESSED_DIR}")
        print("          먼저 전처리를 수행해 data/processed 에 CSV 를 만드세요.")
        return 0

    target_files = _select_target_files(only)
    if not target_files:
        print(f"[build_db] 적재할 CSV 파일이 없습니다: {PROCESSED_DIR}")
        print("          먼저 `python src/preprocess.py` 로 전처리 결과를 만들거나,")
        print("          올바른 파일명을 인자로 전달했는지 확인하세요.")
        return 0

    # DB 폴더가 없으면 생성
    db_path.parent.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    with sqlite3.connect(db_path) as conn:
        for csv_path in target_files:
            table_name = table_name_from(csv_path)
            rel_name = csv_path.relative_to(PROCESSED_DIR).as_posix()
            try:
                df = _read_csv_flexible(csv_path)
            except Exception as exc:  # noqa: BLE001 - 원인을 사용자에게 표시
                print(f"[build_db] 건너뜀: '{rel_name}' 읽기 실패 -> {exc}")
                continue

            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            print(f"[build_db] 저장 완료: 테이블 '{table_name}' <- {rel_name} ({len(df):,} 행)")
            saved_count += 1

    if saved_count:
        print(f"[build_db] 총 {saved_count}개 테이블 저장 -> {db_path}")
    return saved_count


if __name__ == "__main__":
    # 인자가 있으면 해당 파일만, 없으면 전체(코드북 제외) 적재
    only_args = sys.argv[1:] or None
    load_processed_to_db(only=only_args)
