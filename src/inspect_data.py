"""원본 데이터 구조 점검 모듈.

data/raw 폴더 안의 CSV / XLSX 파일을 읽어 행·열 수, 컬럼명, 상위 5행,
결측치 개수, 컬럼별 dtype 등을 출력하고 요약 일부를
data/processed/data_profile_summary.txt 로 저장한다.

실행 방법:
    # 1) (상대)경로 또는 파일명을 인자로 지정
    python src/inspect_data.py youth_life/youth_2024.csv
    python src/inspect_data.py youth_2024.csv

    # 2) 인자 없이 실행하면 data/raw(하위 폴더 포함) 목록을 보여주고 직접 입력받음
    python src/inspect_data.py

주의:
    실제 데이터 파일명을 코드에 하드코딩하지 않는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# 스크립트로 직접 실행할 때(python src/inspect_data.py)도 src 패키지를
# import 할 수 있도록 프로젝트 루트를 모듈 경로에 추가한다.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.preprocess import looks_like_codebook  # noqa: E402

# 프로젝트 루트 기준 경로 (Windows 호환을 위해 pathlib 사용)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SUMMARY_PATH = PROCESSED_DIR / "data_profile_summary.txt"

# CSV 읽기 시 순서대로 시도할 인코딩
CSV_ENCODINGS = ("utf-8", "cp949", "euc-kr")
SUPPORTED_SUFFIXES = (".csv", ".xlsx")


def list_data_files() -> list[Path]:
    """data/raw 폴더(하위 폴더 포함)의 CSV / XLSX 파일 목록을 반환한다.

    출처별 하위 폴더(youth_life/, klips/, eaps/ 등)에 정리해 두어도
    재귀적으로 모두 찾는다.
    """
    if not RAW_DIR.exists():
        return []
    files = [
        p
        for p in sorted(RAW_DIR.rglob("*"))
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return files


def _rel(path: Path) -> str:
    """RAW_DIR 기준 상대경로 문자열(슬래시 통일)을 반환한다."""
    return path.relative_to(RAW_DIR).as_posix()


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
        # 코드북으로 보이는 파일은 표시해 분석 데이터와 구분한다.
        tag = "  [코드북? - 변수 해석용, DB 적재 대상 아님]" if looks_like_codebook(p.name) else ""
        print(f"  {i}. {_rel(p)}{tag}")
    print()

    # 1) 인자로 (상대)경로 또는 파일명이 주어진 경우
    if arg_name:
        return _match_file(arg_name, files)

    # 2) 인자가 없으면 직접 입력 (번호 또는 경로/파일명)
    try:
        choice = input("검사할 파일의 번호 또는 (상대)경로를 입력하세요: ").strip()
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

    return _match_file(choice, files)


def _match_file(name: str, files: list[Path]) -> Path | None:
    """입력한 (상대)경로 또는 파일명을 실제 파일 경로로 해석한다.

    - 정확한 상대경로(youth_life/youth_2024.csv) 우선
    - 그다음 파일명(youth_2024.csv)으로 매칭 (여러 개면 후보를 안내)
    """
    # 1) 상대경로로 바로 매칭
    candidate = RAW_DIR / name
    if candidate.exists() and candidate.is_file():
        return candidate

    # 2) 파일명만으로 매칭
    matches = [p for p in files if p.name == name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"[inspect] 같은 이름의 파일이 여러 개 있습니다. 상대경로로 지정하세요: {name}")
        for p in matches:
            print(f"           - {_rel(p)}")
        return None

    print(f"[inspect] 해당 파일을 data/raw 에서 찾을 수 없습니다: {name}")
    return None


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

    summary = profile_dataframe(df, _rel(target))
    save_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
