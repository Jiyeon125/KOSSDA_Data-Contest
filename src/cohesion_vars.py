"""사회통합실태조사 연도별 변수 매핑.

코드북이 연도마다 PDF·문항번호가 달라, .sav 메타데이터의 **변수 설명(라벨)** 로
동일 개념 문항을 찾는다. 2011·2012는 고립 3문항 체계가 없어 추세 분석에서 제외.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pyreadstat

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "social_cohesion"

# 라벨 키워드(부분 일치) — 변수명(q26/q28/q31 등)은 연도마다 바뀜
ISO_MONEY = "목돈이 필요할 경우 빌릴 수 있는 사람"
ISO_SICK = "몸이 아플 때 도와줄 수 있는 사람"
ISO_TALK = "우울할 때 사적으로 대화할 수 있는 사람"

COMMON_COLS = {
    "weight": "wt1",
    "age_band": "d2",
    "employed": "d6",
    "happiness": "q1_1",
    "life_sat": "q1_4",
}


@dataclass(frozen=True)
class YearMap:
    year: int
    path: Path
    iso_money: str
    iso_sick: str
    iso_talk: str
    weight: str = "wt1"
    age_band: str = "d2"
    employed: str = "d6"
    happiness: str = "q1_1"
    life_sat: str = "q1_4"

    @property
    def iso_cols(self) -> tuple[str, str, str]:
        return self.iso_money, self.iso_sick, self.iso_talk


def _year_from_path(path: Path) -> int:
    m = re.search(r"(\d{4})", path.name)
    if not m:
        raise ValueError(f"연도를 파일명에서 찾을 수 없음: {path.name}")
    return int(m.group(1))


def _find_var_by_label(labels: dict[str, str], must_contain: str,
                       exclude: tuple[str, ...] = ()) -> str | None:
    for var, lab in labels.items():
        ls = str(lab)
        if must_contain not in ls:
            continue
        if any(ex in ls for ex in exclude):
            continue
        return var
    return None


def discover_year_map(path: Path) -> YearMap | None:
    """단일 .sav 에서 표준 변수 매핑을 추출한다. 고립 3문항이 없으면 None."""
    _, meta = pyreadstat.read_sav(str(path), metadataonly=True)
    labels = meta.column_names_to_labels or {}

    money = _find_var_by_label(labels, ISO_MONEY, ("가장 먼저",))
    sick = _find_var_by_label(labels, ISO_SICK, ("가장 먼저",))
    talk = _find_var_by_label(labels, ISO_TALK, ("가장 먼저",))
    if not (money and sick and talk):
        return None

    year = _year_from_path(path)
    cols = {k: v for k, v in COMMON_COLS.items() if v in meta.column_names}
    return YearMap(
        year=year,
        path=path,
        iso_money=money,
        iso_sick=sick,
        iso_talk=talk,
        weight=cols.get("weight", "wt1"),
        age_band=cols.get("age_band", "d2"),
        employed=cols.get("employed", "d6"),
        happiness=cols.get("happiness", "q1_1"),
        life_sat=cols.get("life_sat", "q1_4"),
    )


def list_sav_files() -> list[Path]:
  files = sorted(set(RAW_DIR.glob("*.sav")) | set(RAW_DIR.glob("*.SAV")),
                 key=lambda p: _year_from_path(p))
  return files


def discover_all() -> list[YearMap]:
    maps: list[YearMap] = []
    for p in list_sav_files():
        ym = discover_year_map(p)
        if ym is not None:
            maps.append(ym)
    return maps


def export_registry(out: Path) -> list[YearMap]:
    """연도별 변수 매핑표를 텍스트로 저장한다."""
    maps = discover_all()
    lines = [
        "# 사회통합실태조사 변수 매핑 (라벨 기반 자동 탐색)",
        "",
        "고립 3문항(①목돈 ②아플 때 ③우울·대화)이 동일 척도(1=없다)인 연도만 포함.",
        "2011·2012는 위 3문항 블록이 없어 제외.",
        "",
        "| 연도 | 파일 | 목돈 | 아플 때 | 우울·대화 | 가중 | 연령 | 취업(d6) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in maps:
        lines.append(
            f"| {m.year} | `{m.path.name}` | `{m.iso_money}` | `{m.iso_sick}` | "
            f"`{m.iso_talk}` | `{m.weight}` | `{m.age_band}` | `{m.employed}` |"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return maps
