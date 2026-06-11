"""사회통합실태조사 .sav 변수 탐색 + 연도별 매핑표 생성.

코드북 PDF 형식이 연도마다 달라, .sav 내장 라벨로 동일 문항을 찾는다.
실행: python scripts/cohesion_inspect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.cohesion_vars import discover_all, export_registry, list_sav_files  # noqa: E402


def main() -> int:
    files = list_sav_files()
    if not files:
        print("[cohesion] data/raw/social_cohesion/*.sav 가 없습니다.")
        return 1
    print(f"[cohesion] .sav 파일 {len(files)}개")
    maps = discover_all()
    print(f"[cohesion] 추세 분석 가능 연도 {len(maps)}개: "
          f"{', '.join(str(m.year) for m in maps)}")
    skipped = sorted(set(f.name for f in files) - {m.path.name for m in maps})
    if skipped:
        print(f"[cohesion] 제외(고립 3문항 없음): {', '.join(skipped)}")

    out = _ROOT / "docs" / "social_cohesion_varmap.md"
    export_registry(out)
    print(f"[cohesion] 매핑표 저장: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
