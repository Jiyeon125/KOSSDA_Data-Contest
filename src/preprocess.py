"""원본 데이터 전처리 모듈.

data/raw 의 원본 파일을 읽어 분석에 사용할 형태로 가공한 뒤
data/processed 에 저장하는 함수들을 모아둔다.

주의:
    아직 실제 데이터가 없으므로 아래 함수는 최소한의 골격만 제공한다.
    실제 데이터가 들어오면 컬럼명/결측 처리/타입 변환 로직을 채워 넣으면 된다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로 (src/ 의 부모 디렉터리)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_raw_csv(filename: str, **read_csv_kwargs) -> pd.DataFrame:
    """data/raw 폴더에서 CSV 파일 하나를 읽어 DataFrame 으로 반환한다.

    Args:
        filename: data/raw 안의 파일명 (예: "youth.csv").
        **read_csv_kwargs: pandas.read_csv 에 그대로 전달할 옵션.

    Returns:
        읽어들인 DataFrame.

    Raises:
        FileNotFoundError: 해당 파일이 없을 때.
    """
    path = RAW_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"[preprocess] 원본 파일을 찾을 수 없습니다: {path}")
    return pd.read_csv(path, **read_csv_kwargs)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """기본 정제 로직 골격.

    실제 데이터가 확정되면 이 함수 안에서 결측치 처리, 컬럼명 정리,
    타입 변환 등을 수행한다. 현재는 입력을 그대로 복사해 반환한다.
    """
    cleaned = df.copy()
    # TODO: 실제 데이터 스키마에 맞춰 전처리 로직 추가
    # 예) cleaned = cleaned.dropna(subset=["age"])
    # 예) cleaned.columns = [c.strip().lower() for c in cleaned.columns]
    return cleaned


def save_processed(df: pd.DataFrame, filename: str) -> Path:
    """가공된 DataFrame 을 data/processed 폴더에 CSV 로 저장한다.

    Args:
        df: 저장할 DataFrame.
        filename: 저장할 파일명 (예: "youth_clean.csv").

    Returns:
        저장된 파일의 경로.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / filename
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[preprocess] 저장 완료: {out_path}")
    return out_path


if __name__ == "__main__":
    print("preprocess 모듈 골격입니다. 실제 데이터가 준비되면 함수를 호출하세요.")
