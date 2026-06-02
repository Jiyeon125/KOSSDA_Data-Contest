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


# ======================================================================
# 청년삶실태조사 2024 전용 전처리
#   코드북: data/codebook/2024년_청년삶실태조사_파일설계서.xlsx ('통합' 시트)
#   필터:   경제활동상태==8(비경제활동) AND 지난 주 주된 활동 상태==10(쉬었음)
# ======================================================================

YOUTH_2024_RAW = RAW_DIR / "youth_life" / "2024_총괄_20260527_89328.csv"

# 원본(한글) 컬럼명 -> 분석용 영문 컬럼명
YOUTH_2024_COLMAP: dict[str, str] = {
    "성별": "gender",
    "연령별": "age_group",
    "부모 동거 여부": "live_with_parents",
    "경제활동상태": "econ_status",
    "지난 주 주된 활동 상태": "main_activity",
    "월 평균 총생활비": "living_cost",
    "청년 연간소득 - 총 소득": "income_year",
    "사적 이전소득": "transfer_private",
    "공적 이전소득": "transfer_public",
    "청년 기준 부채 총액": "debt_total",
    "생활비 부채": "debt_living",
    "월평균 이자": "interest_monthly",
    "학자금 부채": "debt_student",
    "주택관련 부채": "debt_housing",
    "삶에 대한 전반적 만족도": "life_satisfaction",
    "삶의 행복감 정도": "happiness",
    "주관적 계층 인식": "subjective_class",
}

# 생활비 부족 시 도움 가능 집단 (복수응답, 1=해당)
_HELP_PREFIX = "(복수 응답) 어려움에 처했을 때 실제로 도움을 받을 수 있는 집단 - 이번 달 생활비가 부족할 때"
YOUTH_2024_HELP_COLMAP: dict[str, str] = {
    f"{_HELP_PREFIX}_(1) 가족": "help_family",
    f"{_HELP_PREFIX}_(2) 지인": "help_acquaintance",
    f"{_HELP_PREFIX}_(3) 공공기관": "help_public",
    f"{_HELP_PREFIX}_(4) 민간기관": "help_private",
    f"{_HELP_PREFIX}_(5) 없음": "help_none",
}

# 코드 -> 라벨 (코드북 확정)
_GENDER_LABEL = {1: "남성", 2: "여성"}
_AGE_LABEL = {1: "19~24세", 2: "25~29세", 3: "30~34세"}
_PARENTS_LABEL = {1: "부모동거", 2: "비동거"}
_CLASS_LABEL = {1: "하층", 2: "중하층", 3: "중간층", 4: "중상층", 5: "상층"}


def _add_labor_group(df: pd.DataFrame) -> pd.Series:
    """경제활동상태/주된활동상태로 노동상태 그룹 라벨을 만든다."""

    def classify(row) -> str:
        econ = row["econ_status"]
        main = row["main_activity"]
        if econ in (1, 2, 3, 4, 5, 6):
            return "취업자"
        if econ == 7:
            return "실업자"
        if econ == 8 and main == 10:
            return "비경활_쉬었음"
        if econ == 8:
            return "비경활_기타"
        return "기타"

    return df.apply(classify, axis=1)


def build_youth_2024(raw_path: Path = YOUTH_2024_RAW) -> dict[str, Path]:
    """청년삶 2024 원본을 분석용 두 테이블로 전처리해 저장한다.

    - youth_2024_all.csv     : 전체 응답자 + labor_group 라벨
    - youth_2024_rested.csv  : 쉬었음 청년(비경활 & 주된활동=쉬었음) 부분집합

    Returns:
        {"all": 경로, "rested": 경로}
    """
    if not raw_path.exists():
        print(f"[preprocess] 오류: 원본을 찾을 수 없습니다 -> {raw_path}")
        print("            data/raw/youth_life/ 에 청년삶 2024 csv 를 넣어주세요.")
        return {}

    # 원본은 cp949 인코딩 (utf-8 -> cp949 순서로 시도)
    df = None
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(raw_path, encoding=enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if df is None:
        print(f"[preprocess] 오류: 인코딩을 해석할 수 없습니다 -> {raw_path}")
        return {}

    # 필요한 원본 컬럼이 모두 있는지 확인 (없으면 친절히 알림)
    needed = list(YOUTH_2024_COLMAP) + list(YOUTH_2024_HELP_COLMAP)
    missing = [c for c in needed if c not in df.columns]
    if missing:
        print("[preprocess] 오류: 코드북 기준 컬럼이 원본에 없습니다:")
        for c in missing:
            print(f"            - {c}")
        return {}

    # 분석용 컬럼 선택 + 영문명으로 변경
    rename_all = {**YOUTH_2024_COLMAP, **YOUTH_2024_HELP_COLMAP}
    work = df[needed].rename(columns=rename_all).copy()

    # 노동상태 그룹 라벨
    work["labor_group"] = _add_labor_group(work)

    # 라벨 컬럼 추가 (원본 코드는 그대로 보존)
    work["gender_label"] = work["gender"].map(_GENDER_LABEL)
    work["age_label"] = work["age_group"].map(_AGE_LABEL)
    work["parents_label"] = work["live_with_parents"].map(_PARENTS_LABEL)
    work["class_label"] = work["subjective_class"].map(_CLASS_LABEL)

    # 파생: 도움 없음 / 도움 있음(가족·지인·공공·민간 중 하나라도)
    help_any = (
        work[["help_family", "help_acquaintance", "help_public", "help_private"]]
        .eq(1)
        .any(axis=1)
    )
    work["has_help"] = help_any.astype(int)
    work["no_help"] = work["help_none"].eq(1).astype(int)

    # 저장 (1) 전체
    all_path = save_processed_csv(work, "youth_life/youth_2024_all.csv")

    # 저장 (2) 쉬었음 부분집합
    rested = work[work["labor_group"] == "비경활_쉬었음"].copy()
    rested_path = save_processed_csv(rested, "youth_life/youth_2024_rested.csv")

    print(f"[preprocess] 전체 {len(work):,}명 / 쉬었음 청년 {len(rested):,}명")
    return {"all": all_path, "rested": rested_path}


# ======================================================================
# 청년삶실태조사 2024 분석용 통합 전처리 (docs/preprocessing_plan.md 기준)
#   산출물: data/processed/youth_life_2024_analysis.csv
#           -> build_db.py 가 youth_life_2024_analysis 테이블로 적재
#   원칙: 분석 변수만 선별 / 코드북 확정 코드만 라벨링 /
#         코드북에 결측코드 정의가 없으므로 9·99 등을 임의 결측 처리하지 않음 /
#         금액 변수의 0 은 '없음'이라는 유효값으로 보존
# ======================================================================

# 분석용 영문명 -> 원본(한글) 컬럼명. (docs/variable_candidates.md §1)
# 원본 컬럼명이 약간 달라도 정규화 매칭으로 견고하게 탐색한다.
YOUTH_2024_ANALYSIS_COLMAP: dict[str, str] = {
    # 인구·배경
    "gender": "성별",
    "age_group": "연령별",
    "edu_final": "최종학력",
    "enroll_status": "귀하의 현재 재학 상태를 응답해 주십시오.",
    "marital": "혼인 상태",
    "live_with_parents": "부모 동거 여부",
    "disability": "장애여부",
    # 노동상태 / 구직 / 취업
    "econ_status": "경제활동상태",
    "main_activity": "지난 주 주된 활동 상태",
    "job_search_4wk": "지난 4주 이내 구직 경험",
    "job_want": "지난 주 직장(일) 희망 여부",
    "job_want_reason_no": "지난 주 직장(일) 비희망 이유",
    "ever_employed": "취업 경험",
    # 생활비 / 소득 / 이전소득
    "living_cost": "월 평균 총생활비",
    "income_year": "청년 연간소득 - 총 소득",
    "hh_income_year": "가구 연간소득 - 총 소득",
    "transfer_private": "사적 이전소득",
    "transfer_public": "공적 이전소득",
    "basic_livelihood": "국민기초생활보장제도(또는 맞춤형 급여) 수급 여부 및 경험",
    # 부채 / 금융부담
    "debt_total": "청년 기준 부채 총액",
    "debt_living": "생활비 부채",
    "debt_student": "학자금 부채",
    "debt_housing": "주택관련 부채",
    "interest_monthly": "월평균 이자",
    "credit_default": "금융 채무 불이행자(신용불량자)에 해당 여부",
    # 자산
    "asset_total": "청년 기준 재산총액",
    "asset_financial": "금융재산",
    # 주거
    "housing_tenure": "현재 주거 점유 형태",
    "housing_type": "현재 거주 주택의 유형",
    # 인식 / 사회적 관계·고립
    "life_satisfaction": "삶에 대한 전반적 만족도",
    "happiness": "삶의 행복감 정도",
    "subjective_class": "주관적 계층 인식",
    "future_feasibility": "바라는 미래에 대한 실현 가능성",
    "outing_freq": "외출 빈도",
    "seclusion_duration": "은둔 생활 상태 지속 기간",
    # 가중치
    "weight_person": "가중치(WT)_모집단 기준(개인)",
}

# 생활비 부족 시 도움 가능 집단(복수응답, 1=해당)
_HELP_LIVING_PREFIX = (
    "(복수 응답) 어려움에 처했을 때 실제로 도움을 받을 수 있는 집단"
    " - 이번 달 생활비가 부족할 때"
)
YOUTH_2024_ANALYSIS_HELP_COLMAP: dict[str, str] = {
    "help_living_family": f"{_HELP_LIVING_PREFIX}_(1) 가족",
    "help_living_acq": f"{_HELP_LIVING_PREFIX}_(2) 지인",
    "help_living_public": f"{_HELP_LIVING_PREFIX}_(3) 공공기관",
    "help_living_private": f"{_HELP_LIVING_PREFIX}_(4) 민간기관",
    "help_living_none": f"{_HELP_LIVING_PREFIX}_(5) 없음",
}

# 코드 -> 라벨 (모두 2024 코드북 확정)
_MARITAL_LABEL = {1: "배우자있음", 2: "미혼", 3: "이혼", 4: "별거", 5: "사별"}
_EDU_LABEL = {
    1: "무학", 2: "초등학교이하", 3: "중학교", 4: "고등학교",
    5: "전문대학", 6: "대학교", 7: "대학원(석사)", 8: "대학원(박사)",
}
_TENURE_LABEL = {
    1: "자가", 2: "전세", 3: "보증부월세", 4: "무보증월세",
    5: "사글세/연세", 6: "일세", 7: "무상거주",
}
_ACTIVITY_LABEL = {
    1: "육아", 2: "가사", 3: "정규교육통학", 4: "입시학원통학",
    5: "취업학원통학", 6: "취업준비", 7: "진학준비", 8: "질병요양",
    9: "군입대대기", 10: "쉬었음", 11: "기타",
}

# 금액·연속형(수치 강제 변환 대상). 0 은 유효값으로 보존한다.
_NUMERIC_COLS = [
    "living_cost", "income_year", "hh_income_year",
    "transfer_private", "transfer_public",
    "debt_total", "debt_living", "debt_student", "debt_housing",
    "interest_monthly", "asset_total", "asset_financial",
    "life_satisfaction", "happiness", "weight_person",
]


def _normalize_key(name: object) -> str:
    """컬럼명 매칭용 정규화 키. 공백·특수문자를 제거하고 소문자화한다."""
    text = str(name).strip().lower()
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def _read_csv_fallback(path: Path) -> pd.DataFrame | None:
    """인코딩 폴백(utf-8 -> cp949 -> euc-kr)으로 CSV 를 읽는다."""
    for enc in ("utf-8", "cp949", "euc-kr", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def _resolve_columns(
    df: pd.DataFrame, colmap: dict[str, str]
) -> tuple[dict[str, str], list[str]]:
    """{분석명: 원본명} 매핑을 실제 컬럼에 견고하게 연결한다.

    1) 원본명이 그대로 있으면 사용,
    2) 없으면 정규화 키로 매칭(공백/특수문자 차이 흡수),
    3) 그래도 없으면 누락 목록에 기록(중단하지 않음).

    Returns:
        (rename: {원본실제컬럼 -> 분석명}, missing: [매칭 실패한 분석명])
    """
    norm_to_actual: dict[str, str] = {}
    for col in df.columns:
        norm_to_actual.setdefault(_normalize_key(col), col)

    rename: dict[str, str] = {}
    missing: list[str] = []
    for analysis_name, raw_name in colmap.items():
        if raw_name in df.columns:
            rename[raw_name] = analysis_name
        else:
            actual = norm_to_actual.get(_normalize_key(raw_name))
            if actual is not None:
                rename[actual] = analysis_name
            else:
                missing.append(analysis_name)
    return rename, missing


def _gt0_flag(series: pd.Series) -> pd.Series:
    """양수(>0)면 1, 0이면 0, 결측이면 결측(NaN)으로 두는 플래그."""
    s = pd.to_numeric(series, errors="coerce")
    return s.gt(0).where(s.notna()).astype("Int64")


def _print_validation(df: pd.DataFrame, total_raw: int) -> None:
    """기본 검증 출력: 행수·쉬었음 분포·결측률·노동상태별 요약."""
    print("\n" + "=" * 60)
    print("[검증] 청년삶 2024 분석용 데이터")
    print("=" * 60)
    print(f"- 원본 전체 행 수        : {total_raw:,}")
    print(f"- 청년 필터 후 행 수     : {len(df):,}")

    if "is_rested" in df.columns:
        vc = df["is_rested"].value_counts(dropna=False).sort_index()
        print("- 쉬었음 여부 분포(is_rested):")
        for k, v in vc.items():
            label = "쉬었음" if k == 1 else ("비쉬었음" if k == 0 else "결측")
            print(f"    {label}({k}): {v:,} ({v / len(df) * 100:.1f}%)")

    if "labor_group" in df.columns:
        print("- 노동상태 그룹 분포:")
        for k, v in df["labor_group"].value_counts(dropna=False).items():
            print(f"    {k}: {v:,} ({v / len(df) * 100:.1f}%)")

    key_vars = [
        "gender", "age_group", "live_with_parents", "econ_status",
        "main_activity", "living_cost", "income_year", "debt_total",
        "interest_monthly", "subjective_class", "life_satisfaction",
        "help_living_family", "help_living_none",
    ]
    print("- 주요 변수 결측률(%):")
    for col in key_vars:
        if col in df.columns:
            miss = df[col].isna().mean() * 100
            print(f"    {col:<20}: {miss:5.1f}")

    if "labor_group" in df.columns:
        means_cols = [c for c in ["living_cost", "income_year", "debt_total",
                                  "interest_monthly", "subjective_class",
                                  "life_satisfaction"] if c in df.columns]
        if means_cols:
            print("- 노동상태별 주요 변수 평균:")
            grp = df.groupby("labor_group")[means_cols].mean(numeric_only=True)
            with pd.option_context("display.width", 200,
                                   "display.float_format", lambda x: f"{x:,.1f}"):
                print(grp.to_string())
    print("=" * 60 + "\n")


def build_youth_2024_analysis(
    raw_path: Path = YOUTH_2024_RAW,
    save: bool = True,
) -> pd.DataFrame | None:
    """청년삶 2024 원본을 분석용 통합 데이터셋으로 전처리한다.

    단계 (docs/preprocessing_plan.md §1):
      1) 분석 변수만 선별(견고한 컬럼 매칭)
      2) 청년 연령대 필터(age_group ∈ {1,2,3} = 19~34세)
      3) 노동상태/쉬었음/취업/구직 변수 생성
      4) 경제·주거·생활조건 라벨 정리
      5) 코드북 기준 결측만 처리(임의 9·99 결측화 금지)
      6) data/processed/youth_life_2024_analysis.csv 저장

    Returns:
        분석용 DataFrame (실패 시 None).
    """
    if not raw_path.exists():
        print(f"[preprocess] 오류: 원본을 찾을 수 없습니다 -> {raw_path}")
        print("            data/raw/youth_life/ 에 청년삶 2024 csv 를 넣어주세요.")
        return None

    df = _read_csv_fallback(raw_path)
    if df is None:
        print(f"[preprocess] 오류: 인코딩을 해석할 수 없습니다 -> {raw_path}")
        return None

    total_raw = len(df)

    # (1) 분석 변수 선별 ----------------------------------------------------
    full_map = {**YOUTH_2024_ANALYSIS_COLMAP, **YOUTH_2024_ANALYSIS_HELP_COLMAP}
    rename, missing = _resolve_columns(df, full_map)
    if missing:
        print(f"[preprocess] 경고: 원본에서 찾지 못한 변수 {len(missing)}개 -> {missing}")
        print("            (해당 변수는 제외하고 계속 진행합니다.)")
    # 쉬었음 식별에 필수인 컬럼이 없으면 중단
    essential = {"econ_status", "main_activity", "age_group"}
    have = set(rename.values())
    if not essential.issubset(have):
        print(f"[preprocess] 오류: 필수 변수 누락 -> {essential - have}")
        return None

    work = df[list(rename)].rename(columns=rename).copy()

    # (5-a) 수치형 강제 변환 (0 은 유효값으로 보존, 빈칸/문자는 NaN)
    for col in _NUMERIC_COLS:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    # (2) 청년 연령대 필터 (age_group 1=19~24, 2=25~29, 3=30~34) ----------
    before = len(work)
    work = work[work["age_group"].isin([1, 2, 3])].copy()
    print(f"[preprocess] 청년 연령 필터: {before:,} -> {len(work):,} 행")

    # (3) 노동상태 / 쉬었음 / 취업 / 구직 변수 -----------------------------
    work["labor_group"] = _add_labor_group(work)
    work["is_employed"] = work["econ_status"].isin([1, 2, 3, 4, 5, 6]).astype(int)
    work["is_unemployed"] = work["econ_status"].eq(7).astype(int)
    work["is_rested"] = (
        work["econ_status"].eq(8) & work["main_activity"].eq(10)
    ).astype(int)
    if "job_search_4wk" in work.columns:
        # 1 = 구해 보았음
        work["is_job_seeking"] = work["job_search_4wk"].eq(1).astype("Int64")

    # (4) 코드 라벨 정리 (원본 코드는 보존, *_label 추가) -------------------
    label_specs = [
        ("gender", _GENDER_LABEL, "gender_label"),
        ("age_group", _AGE_LABEL, "age_label"),
        ("live_with_parents", _PARENTS_LABEL, "parents_label"),
        ("subjective_class", _CLASS_LABEL, "class_label"),
        ("marital", _MARITAL_LABEL, "marital_label"),
        ("edu_final", _EDU_LABEL, "edu_label"),
        ("housing_tenure", _TENURE_LABEL, "housing_tenure_label"),
        ("main_activity", _ACTIVITY_LABEL, "main_activity_label"),
    ]
    for src_col, mapping, new_col in label_specs:
        if src_col in work.columns:
            work[new_col] = work[src_col].map(mapping)

    # 생활비 지원망 플래그 (복수응답 1=해당)
    help_cols = [c for c in ["help_living_family", "help_living_acq",
                             "help_living_public", "help_living_private"]
                 if c in work.columns]
    if help_cols:
        work["has_help"] = work[help_cols].eq(1).any(axis=1).astype(int)
    if "help_living_family" in work.columns:
        work["family_help_flag"] = work["help_living_family"].eq(1).astype(int)
    if "help_living_none" in work.columns:
        work["no_help_flag"] = work["help_living_none"].eq(1).astype(int)
    if "live_with_parents" in work.columns:
        work["not_parent_cohabit"] = work["live_with_parents"].eq(2).astype(int)

    # 금융부담/소득지원 보유 플래그 (>0)
    flag_specs = [
        ("debt_total", "has_debt"),
        ("debt_living", "has_living_cost_debt"),
        ("interest_monthly", "has_interest"),
        ("transfer_private", "has_private_transfer"),
        ("transfer_public", "has_public_transfer"),
    ]
    for src_col, new_col in flag_specs:
        if src_col in work.columns:
            work[new_col] = _gt0_flag(work[src_col])

    # 사회적 고립 성향(외출빈도 7~8 = 방/집에서 거의 안 나옴) — 해석 주의
    if "outing_freq" in work.columns:
        work["isolation_flag"] = work["outing_freq"].isin([7, 8]).astype("Int64")

    # (1-8) 생활안전망 취약점수(0~6). 이전소득 없음은 가산 제외.
    #        결측 플래그는 0으로 보아 가산(보수적), 해석은 쉬었음 집단 중심.
    vuln_parts = []
    if "not_parent_cohabit" in work.columns:
        vuln_parts.append(work["not_parent_cohabit"].fillna(0))
    if "family_help_flag" in work.columns:
        vuln_parts.append((1 - work["family_help_flag"]).clip(lower=0))
    if "no_help_flag" in work.columns:
        vuln_parts.append(work["no_help_flag"].fillna(0))
    for c in ["has_debt", "has_living_cost_debt", "has_interest"]:
        if c in work.columns:
            vuln_parts.append(work[c].astype("Float64").fillna(0))
    if vuln_parts:
        work["vuln_score"] = sum(vuln_parts).astype(int)

    # 조사연도 파생
    work["survey_year"] = 2024

    # (6) 저장 -------------------------------------------------------------
    if save:
        save_processed_csv(work, "youth_life_2024_analysis.csv")

    _print_validation(work, total_raw)
    return work


def main() -> int:
    """전처리 파이프라인 진입점.

    청년삶 2024 분석용 통합 데이터셋을 생성한다.
    (다른 데이터 전처리가 추가되면 여기에 함수를 더 호출한다.)
    """
    print("[preprocess] 청년삶 2024 분석용 전처리 시작...")
    result = build_youth_2024_analysis()
    if result is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
