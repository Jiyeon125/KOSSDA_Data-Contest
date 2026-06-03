"""KLIPS 코드북(개인/가구)에서 분석 후보 변수명을 식별한다.

CUM0066 누적 코드북의 '개인용'/'가구용' 시트는
  col1=변수설명, col2=통합변수명, col3 이후=차수별 응답수
구조다. 핵심 키워드로 변수명을 찾아 wave26 데이터 컬럼과 대조한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CODEBOOK_DIR = ROOT / "data" / "codebook"
KLIPS_DIR = ROOT / "data" / "raw" / "klips"

PERSON_KEYS = ["성별", "만나이", "연령", "출생", "경제활동", "종사상", "취업",
               "구직", "실업", "임금", "근로소득", "월평균", "교육", "졸업",
               "학력", "혼인", "주당", "근로시간"]
HH_KEYS = ["가구소득", "가구총소득", "경상소득", "부채", "자산", "주거", "점유",
           "생활비", "가구원수"]


def _find_codebook() -> Path | None:
    for p in CODEBOOK_DIR.glob("*.xls"):
        try:
            names = pd.ExcelFile(p, engine="xlrd").sheet_names
        except Exception:  # noqa: BLE001
            continue
        if "개인용" in names and "가구용" in names:
            return p
    return None


def _scan_sheet(path: Path, sheet: str, keys: list[str]) -> list[tuple[str, str]]:
    d = pd.read_excel(path, sheet_name=sheet, engine="xlrd", header=None)
    desc, var = d[1].astype(str), d[2].astype(str)
    out: list[tuple[str, str]] = []
    seen = set()
    for i in range(len(d)):
        dv, vv = desc.iloc[i].strip(), var.iloc[i].strip()
        if vv in ("nan", "") or len(vv) > 13:
            continue
        if any(k in dv for k in keys) and vv not in seen:
            seen.add(vv)
            out.append((dv[:40], vv))
    return out


def _wave26_cols(kind: str) -> list[str]:
    f = KLIPS_DIR / f"kor_data_CUM0066_klips26{kind}.xlsx"
    return list(pd.read_excel(f, engine="calamine", nrows=1).columns)


def main() -> int:
    cb = _find_codebook()
    if cb is None:
        print("[klips_map] 개인용/가구용 시트를 가진 코드북을 찾지 못했습니다.")
        return 1
    print(f"[klips_map] 코드북: {cb.name}\n")

    p_cols = set(_wave26_cols("p"))
    h_cols = set(_wave26_cols("h"))

    print("===== 개인용 후보 (변수설명 -> 통합변수명 | wave26 컬럼) =====")
    for dv, vv in _scan_sheet(cb, "개인용", PERSON_KEYS):
        # 누적 변수명의 '__' 는 차수 placeholder -> 26 으로 치환해 대조
        cand = vv.replace("p__", "p26")
        exists = cand in p_cols or vv in p_cols
        if not exists:
            continue
        shown = cand if cand in p_cols else vv
        print(f"  [O] {dv:42s} -> {shown}")

    print("\n===== 가구용 후보 =====")
    for dv, vv in _scan_sheet(cb, "가구용", HH_KEYS):
        cand = vv.replace("h__", "h26")
        exists = cand in h_cols or vv in h_cols
        if not exists:
            continue
        shown = cand if cand in h_cols else vv
        print(f"  [O] {dv:42s} -> {shown}")

    print(f"\n[klips_map] wave26 person 컬럼 수={len(p_cols)}, household 컬럼 수={len(h_cols)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
