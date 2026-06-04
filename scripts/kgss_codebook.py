"""KGSS .sav에서 사람이 열어볼 수 있는 변수목록을 추출한다.

- outputs/kgss_codebook_all.csv : 전체 변수(이름·라벨·값레이블) — 엑셀로 열람
- outputs/kgss_candidate_vars.md : 우리 주제 후보변수 + 연도별 응답가능 — 검토용

실행: python scripts/kgss_codebook.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

_ROOT = Path(__file__).resolve().parents[1]
OUT = _ROOT / "outputs"

# 우리 주제 후보(고립·웰빙·노동·계층·인구)
CANDIDATES = [
    "YEAR", "FINALWT", "AGE", "SEX", "EDUC", "MARITAL",
    "HAPPINSS", "SATFACE6", "FEELDOWN",            # 웰빙
    "BESTFRND", "OTHREL4", "NEIFRD",               # 고립/관계
    "DOWN1", "SICK1", "BORROW1",                   # 사회적 지지(없음)
    "EMPLY", "WHYNOE", "WHYUNEM", "UNWKEXA",       # 고용/미취업
    "INCOME", "FINRELA", "STDLIVIN",               # 소득/계층
]


def main() -> int:
    path = glob.glob(str(_ROOT / "data/raw/kgss/*.sav"))
    if not path:
        raise SystemExit("[kgss] data/raw/kgss/*.sav 없음")
    path = path[0]

    # 1) 전체 변수 메타데이터 → CSV
    _, meta = pyreadstat.read_sav(path, metadataonly=True)
    rows = []
    for name in meta.column_names:
        label = meta.column_names_to_labels.get(name) or ""
        vlabs = meta.variable_value_labels.get(name, {})
        vl = "; ".join(f"{k}={v}" for k, v in list(vlabs.items()))
        rows.append({"변수명": name, "설명": label, "값레이블": vl})
    allcsv = OUT / "kgss_codebook_all.csv"
    pd.DataFrame(rows).to_csv(allcsv, index=False, encoding="utf-8-sig")
    print(f"[kgss] 전체 변수 {len(rows)}개 → {allcsv}")

    # 2) 후보변수 연도별 응답가능 + 값레이블 → MD
    use = [c for c in CANDIDATES if c in meta.column_names]
    df, _ = pyreadstat.read_sav(path, usecols=use)
    years = sorted(df.YEAR.dropna().unique().astype(int))
    lines = ["# KGSS 후보변수 검토표", "",
             f"- 파일: `{Path(path).name}`  /  전체 {len(rows)}변수 · {len(df):,}행",
             f"- 조사연도: {years}", "",
             "> '응답가능 연도' = 그 해 실제 조사된 연도(값 ≥ 0 존재). 빈칸=미조사.", ""]
    for c in use:
        if c in ("YEAR", "FINALWT"):
            continue
        label = meta.column_names_to_labels.get(c) or ""
        avail = [str(y) for y in years
                 if (df.loc[df.YEAR == y, c] >= 0).sum() > 0]
        vlabs = meta.variable_value_labels.get(c, {})
        vl = ", ".join(f"{int(k) if float(k).is_integer() else k}={v}"
                       for k, v in list(vlabs.items())[:10])
        lines.append(f"### `{c}` — {label}")
        lines.append(f"- 응답가능 연도: {', '.join(avail) if avail else '(상시/연속)'}")
        lines.append(f"- 값: {vl}")
        lines.append("")
    md = OUT / "kgss_candidate_vars.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[kgss] 후보변수 검토표 → {md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
