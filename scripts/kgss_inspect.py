"""KGSS(한국종합사회조사) .sav/.dta 변수 탐색기.

SPSS/Stata 프로그램 없이 pyreadstat 으로 변수설명·값레이블(코드북)을 추출해
우리 주제(고립·웰빙·고용·계층)에 맞는 변수를 자동으로 찾아준다.

사용:
  1) KOSSDA에서 받은 KGSS 파일을 data/raw/kgss/ 에 넣는다(.sav 또는 .dta).
  2) python scripts/kgss_inspect.py            # 폴더에서 자동으로 첫 파일 사용
     python scripts/kgss_inspect.py 파일명.sav  # 특정 파일 지정

출력: 전체 변수 수 + 주제 키워드에 걸리는 변수(변수명·설명·값레이블).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pyreadstat

_ROOT = Path(__file__).resolve().parents[1]
KGSS_DIR = _ROOT / "data" / "raw" / "kgss"

# 주제별 키워드(변수 '설명'에서 검색) — 한글 라벨 기준
THEMES: dict[str, list[str]] = {
    "웰빙/만족": ["만족", "행복", "삶의", "건강", "우울", "외로", "자살"],
    "고립/관계": ["고립", "관계", "친구", "만남", "연락", "신뢰", "도움", "이웃",
                "모임", "교류", "사회적", "연결망", "지지"],
    "고용/노동": ["경제활동", "취업", "실업", "일자리", "직업", "종사", "근로", "구직", "고용"],
    "계층/소득": ["계층", "소득", "생활수준", "재산", "빈곤", "지위"],
    "인구": ["연령", "나이", "출생", "성별", "혼인", "교육", "학력", "가구"],
}


def _find_file(arg: str | None) -> Path | None:
    if arg:
        p = KGSS_DIR / arg
        return p if p.exists() else None
    for ext in ("*.sav", "*.dta", "*.SAV", "*.DTA"):
        files = sorted(KGSS_DIR.glob(ext))
        if files:
            return files[0]
    return None


def _read_meta(path: Path):
    """전체 데이터 로딩 없이 메타데이터(변수·레이블)만 빠르게 읽는다."""
    reader = pyreadstat.read_sav if path.suffix.lower() == ".sav" else pyreadstat.read_dta
    _, meta = reader(str(path), metadataonly=True)
    return meta


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = _find_file(arg)
    if path is None:
        print("[kgss] 파일을 찾지 못했습니다. data/raw/kgss/ 에 .sav 또는 .dta 를 넣어주세요.")
        print(f"       (현재 폴더: {KGSS_DIR})")
        return 1

    print(f"[kgss] 파일: {path.name}")
    meta = _read_meta(path)
    labels: dict[str, str] = meta.column_names_to_labels or {}
    val_labels = meta.variable_value_labels or {}
    print(f"[kgss] 변수 총 {len(meta.column_names)}개, 표본 {meta.number_rows}행\n")

    matched: set[str] = set()
    for theme, keys in THEMES.items():
        hits = []
        for var, lab in labels.items():
            lab_s = str(lab)
            if any(k in lab_s for k in keys):
                hits.append((var, lab_s))
        if not hits:
            continue
        print(f"===== [{theme}] {len(hits)}개 =====")
        for var, lab in hits[:25]:
            matched.add(var)
            vl = val_labels.get(var)
            vl_str = ""
            if vl:
                items = list(vl.items())[:6]
                vl_str = " | 값: " + ", ".join(f"{k}={v}" for k, v in items)
                if len(vl) > 6:
                    vl_str += " …"
            print(f"  {var:14s} {lab[:40]:40s}{vl_str}")
        print()

    print(f"[kgss] 주제 매칭 변수 {len(matched)}개. 위 목록에서 분석 변수를 확정하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
