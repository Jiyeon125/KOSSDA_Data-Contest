"""원본 데이터 전처리 모듈 (범용 함수 모음).

아직 실제 데이터의 구체적인 컬럼명이 확정되지 않았으므로,
특정 데이터에 종속되지 않는 범용 전처리 함수들을 제공한다.
실제 컬럼이 확정되면 main() 안에서 이 함수들을 조합해 사용한다.

실행 방법:
    python src/preprocess.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

# 프로젝트 루트 기준 경로 (Windows 호환을 위해 pathlib 사용)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# 파일명에 포함되면 '코드북(변수 해석용 참고자료)'으로 간주할 키워드.
# 코드북은 분석 데이터가 아니므로 DB 적재 대상에서 제외한다.
CODEBOOK_KEYWORDS = ("codebook", "code_book", "코드북", "변수설명", "변수정의", "layout")


def looks_like_codebook(name: str) -> bool:
    """파일명이 코드북으로 보이는지 판단한다.

    코드북 파일과 실제 분석 데이터 파일을 구분하기 위한 휴리스틱이다.
    (예: "klips_codebook.xlsx", "청년삶_코드북.csv" -> True)
    """
    lowered = str(name).lower()
    return any(keyword in lowered for keyword in CODEBOOK_KEYWORDS)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명을 정규화한다.

    - 앞뒤 공백 제거
    - 영문 소문자화
    - 공백/연속 공백을 단일 언더스코어(_)로 치환
    - 영문/숫자/언더스코어/한글 외 특수문자 제거

    원본 DataFrame 은 변경하지 않고 복사본을 반환한다.
    """
    cleaned = df.copy()

    def _clean(name: object) -> str:
        text = str(name).strip().lower()
        # 공백류를 언더스코어로
        text = re.sub(r"\s+", "_", text)
        # 한글, 영문, 숫자, 언더스코어만 남기고 제거
        text = re.sub(r"[^0-9a-z_가-힣]", "", text)
        # 연속 언더스코어 정리 및 양 끝 언더스코어 제거
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "col"

    cleaned.columns = [_clean(c) for c in cleaned.columns]
    return cleaned


def select_columns(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """필요한 컬럼만 선택해 반환한다.

    Args:
        df: 입력 DataFrame.
        columns: 선택할 컬럼명 목록.

    Raises:
        KeyError: 존재하지 않는 컬럼을 요청했을 때.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(
            f"[preprocess] 존재하지 않는 컬럼: {missing}\n"
            f"             사용 가능한 컬럼: {list(df.columns)}"
        )
    return df.loc[:, list(columns)].copy()


def replace_missing_codes(
    df: pd.DataFrame,
    missing_codes: Iterable,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """특정 코드값(예: -9, 99, "모름")을 결측치(NaN)로 변환한다.

    설문 데이터는 무응답/모름 등을 특수 코드로 표기하는 경우가 많다.

    Args:
        df: 입력 DataFrame.
        missing_codes: 결측으로 처리할 값들의 목록.
        columns: 적용할 컬럼 목록. None 이면 전체 컬럼에 적용.

    Returns:
        결측 코드가 NaN 으로 치환된 복사본.
    """
    cleaned = df.copy()
    target_cols = list(columns) if columns is not None else list(cleaned.columns)
    codes = list(missing_codes)
    cleaned[target_cols] = cleaned[target_cols].replace(codes, pd.NA)
    return cleaned


def save_processed_csv(df: pd.DataFrame, file_name: str) -> Path:
    """전처리된 DataFrame 을 data/processed 폴더에 CSV 로 저장한다.

    Args:
        df: 저장할 DataFrame.
        file_name: 저장할 파일명 또는 상대경로
            (예: "youth_clean.csv" 또는 "youth_life/youth_2024_clean.csv").
            확장자가 없으면 .csv 를 붙인다.

    Returns:
        저장된 파일 경로.
    """
    name = file_name if file_name.lower().endswith(".csv") else f"{file_name}.csv"
    out_path = PROCESSED_DIR / name
    # 하위 폴더 경로가 포함될 수 있으므로 부모 디렉터리까지 생성
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 한글 깨짐 방지를 위해 utf-8-sig 사용
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[preprocess] 저장 완료: {out_path} ({len(df):,} 행)")
    return out_path


def main() -> int:
    """전처리 파이프라인 진입점 (골격).

    실제 컬럼이 확정되면 아래 흐름을 채워 넣는다:
        1) data/raw 에서 원본 읽기 (inspect_data.read_data_file 활용 가능)
        2) normalize_column_names
        3) replace_missing_codes
        4) select_columns
        5) save_processed_csv
    """
    print("[preprocess] 범용 전처리 함수 모듈입니다.")
    print("            실제 컬럼이 확정되면 main() 안에서 함수를 조합해 사용하세요.")
    print(f"            원본 폴더:   {RAW_DIR}")
    print(f"            저장 폴더:   {PROCESSED_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
