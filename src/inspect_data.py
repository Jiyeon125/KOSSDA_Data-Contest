"""원본 데이터 구조 점검 모듈.

data/raw 폴더 안의 CSV / XLSX 파일을 읽어 행·열 수, 컬럼명, 상위 5행,
결측치 개수, 컬럼별 dtype 등을 출력하고 요약 일부를
data/processed/data_profile_summary.txt 로 저장한다.

실행 방법:
    # 1) 파일명을 인자로 지정
    python src/inspect_data.py youth.csv

    # 2) 인자 없이 실행하면 data/raw 목록을 보여주고 직접 입력받음
    python src/inspect_data.py

주의:
    실제 데이터 파일명을 코드에 하드코딩하지 않는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# 프로젝트 루트 기준 경로 (Windows 호환을 위해 pathlib 사용)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SUMMARY_PATH = PROCESSED_DIR / "data_profile_summary.txt"

# CSV 읽기 시 순서대로 시도할 인코딩
CSV_ENCODINGS = ("utf-8", "cp949", "euc-kr")
SUPPORTED_SUFFIXES = (".csv", ".xlsx")


def list_data_files() -> list[Path]:
    """data/raw 폴더의 CSV / XLSX 파일 목록을 반환한다."""
    if not RAW_DIR.exists():
        return []
    files = [
        p
        for p in sorted(RAW_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return files


def read_data_file(path: Path) -> pd.DataFrame:
    """확장자에 맞춰 CSV / XLSX 파일을 DataFrame 으로 읽는다.

    CSV 는 utf-8 -> cp949 -> euc-kr 순으로 인코딩을 시도한다.

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: 지원하지 않는 확장자거나 모든 인코딩이 실패했을 때.
    """
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        last_error: Exception | None = None
        for encoding in CSV_ENCODINGS:
            try:
                df = pd.read_csv(path, encoding=encoding)
                print(f"  - CSV 인코딩 '{encoding}' 으로 읽기 성공")
                return df
            except (UnicodeDecodeError, UnicodeError) as exc:
                last_error = exc
                continue
        raise ValueError(
            f"CSV 인코딩 시도 실패 ({', '.join(CSV_ENCODINGS)}): {last_error}"
        )

    if suffix == ".xlsx":
        return pd.read_excel(path)

    raise ValueError(f"지원하지 않는 확장자입니다: {suffix} (csv, xlsx 만 지원)")


def profile_dataframe(df: pd.DataFrame, source_name: str) -> str:
    """DataFrame 의 기본 프로파일 문자열을 만들어 콘솔에 출력하고 반환한다."""
    lines: list[str] = []

    def emit(text: str = "") -> None:
        """콘솔 출력과 요약 문자열 누적을 함께 처리."""
        print(text)
        lines.append(text)

    emit("=" * 60)
    emit(f"[데이터 프로파일] {source_name}")
    emit("=" * 60)

    emit(f"행 수 (rows): {df.shape[0]:,}")
    emit(f"열 수 (cols): {df.shape[1]:,}")
    emit("")

    emit("[컬럼명 목록]")
    for i, col in enumerate(df.columns, start=1):
        emit(f"  {i:>3}. {col}")
    emit("")

    emit("[상위 5행]")
    emit(df.head().to_string())
    emit("")

    emit("[결측치 개수]")
    emit(df.isna().sum().to_string())
    emit("")

    emit("[컬럼별 dtype]")
    emit(df.dtypes.astype(str).to_string())
    emit("")

    return "\n".join(lines)


def save_summary(summary_text: str) -> Path:
    """프로파일 요약을 data/processed/data_profile_summary.txt 로 저장한다."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(summary_text, encoding="utf-8")
    print(f"[inspect] 요약 저장 완료 -> {SUMMARY_PATH}")
    return SUMMARY_PATH


def resolve_target_file(arg_name: str | None) -> Path | None:
    """검사 대상 파일 경로를 결정한다.

    인자로 파일명이 주어지면 그것을 사용하고, 없으면 목록을 보여준 뒤
    사용자 입력을 받는다. 적절한 대상이 없으면 None 을 반환한다.
    """
    files = list_data_files()

    if not files:
        print(f"[inspect] data/raw 에 csv/xlsx 파일이 없습니다: {RAW_DIR}")
        print("          원본 데이터를 data/raw/ 에 넣은 뒤 다시 실행하세요.")
        return None

    print("[inspect] data/raw 에서 발견한 데이터 파일:")
    for i, p in enumerate(files, start=1):
        print(f"  {i}. {p.name}")
    print()

    # 1) 인자로 파일명이 주어진 경우
    if arg_name:
        target = RAW_DIR / arg_name
        if not target.exists():
            print(f"[inspect] 지정한 파일이 data/raw 에 없습니다: {arg_name}")
            return None
        return target

    # 2) 인자가 없으면 직접 입력 (번호 또는 파일명)
    try:
        choice = input("검사할 파일의 번호 또는 파일명을 입력하세요: ").strip()
    except EOFError:
        print("[inspect] 입력이 없어 종료합니다. 파일명을 인자로 넘겨도 됩니다.")
        return None

    if not choice:
        print("[inspect] 입력이 비어 있어 종료합니다.")
        return None

    # 번호로 선택한 경우
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(files):
            return files[idx - 1]
        print(f"[inspect] 잘못된 번호입니다: {idx}")
        return None

    # 파일명으로 선택한 경우
    target = RAW_DIR / choice
    if not target.exists():
        print(f"[inspect] 해당 파일이 data/raw 에 없습니다: {choice}")
        return None
    return target


def main(argv: list[str]) -> int:
    arg_name = argv[1] if len(argv) > 1 else None

    target = resolve_target_file(arg_name)
    if target is None:
        return 1

    try:
        df = read_data_file(target)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[inspect] 오류: {exc}")
        return 1

    summary = profile_dataframe(df, target.name)
    save_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
