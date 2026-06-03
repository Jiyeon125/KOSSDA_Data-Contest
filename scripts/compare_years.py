"""보강분석 — 청년삶 2022 vs 2024 재현성 비교.

같은 정의(쉬었음=비경활&주된활동=쉬었음)와 같은 파생규칙으로 두 해를 처리해
(1) 쉬었음 규모, (2) 쉬었음 내부 취약지표, (3) 군집 하위유형이
2024에서만의 우연인지, 2022에서도 재현되는지 확인한다.

실행: python scripts/compare_years.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import clustering as cl  # noqa: E402
from src import queries as q  # noqa: E402
from scripts.insights import _setup_font, _save  # noqa: E402

YEAR_COLORS = {2022: "#9D7660", 2024: "#4C78A8"}
# 쉬었음 내부 취약지표(군집 입력과 동일) + 표시 라벨
FLAGS = {
    "no_help_flag": "지원망 없음",
    "not_parent_cohabit": "부모 비동거",
    "has_debt": "부채 보유",
    "has_interest": "이자 부담",
    "isolation_flag": "고립 경향",
}
CONT = {"life_satisfaction": "삶 만족도", "happiness": "행복감",
        "subjective_class": "주관 계층"}


def _load(year: int) -> pd.DataFrame:
    return q.run_query(f"SELECT * FROM youth_life_{year}_analysis")


def _rested(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_rested"] == 1].copy()


def main() -> int:
    _setup_font()
    d22, d24 = _load(2022), _load(2024)
    r22, r24 = _rested(d22), _rested(d24)

    # === 1) 쉬었음 규모(청년 전체 대비, 가중) ===
    print("=" * 64)
    print("[1] 쉬었음 규모 — 청년 전체 대비")
    rows_size = []
    for yr, d in ((2022, d22), (2024, d24)):
        s = q.weighted_share(d, "is_rested")
        rows_size.append({"연도": yr, "표본_쉬었음": s["표본n"], "청년표본": len(d),
                          "쉬었음_가중(%)": s["비율_가중(%)"],
                          "쉬었음_비가중(%)": s["비율_비가중(%)"],
                          "모집단추정(명)": s["모집단추정(명)"]})
    size_df = pd.DataFrame(rows_size)
    print(size_df.to_string(index=False))

    # === 2) 쉬었음 내부 취약지표 (가중 비율) + 연도 간 검정(비가중) ===
    print("\n" + "=" * 64)
    print("[2] 쉬었음 내부 취약지표 — 2022 vs 2024")
    both = pd.concat([r22, r24], ignore_index=True)
    rows = []
    for col, label in FLAGS.items():
        w22 = q.weighted_share(r22, col)["비율_가중(%)"]
        w24 = q.weighted_share(r24, col)["비율_가중(%)"]
        test = q.chi_square_compare(both, "survey_year", col, 2022, 2024)
        rows.append({"지표": label, "2022_가중%": w22, "2024_가중%": w24,
                     "p": None if test["p"] is None else round(test["p"], 4),
                     "효과V": test.get("효과크기V"), "유의": test.get("유의"),
                     "경고": test.get("경고", "")})
    flag_df = pd.DataFrame(rows)
    print(flag_df.to_string(index=False))

    # === 3) 웰빙(연속형) 가중 평균 + Mann-Whitney ===
    print("\n" + "=" * 64)
    print("[3] 쉬었음 웰빙 — 2022 vs 2024")
    rows_c = []
    for col, label in CONT.items():
        m22, m24 = q.weighted_mean(r22, col), q.weighted_mean(r24, col)
        test = q.mann_whitney_compare(both, "survey_year", col, 2022, 2024)
        rows_c.append({"지표": label, "2022_가중평균": m22, "2024_가중평균": m24,
                       "p": None if test["p"] is None else round(test["p"], 4),
                       "효과r": test["효과크기r"], "유의": test["유의"]})
    cont_df = pd.DataFrame(rows_c)
    print(cont_df.to_string(index=False))

    # === 4) 군집 하위유형 재현성 (2022 rested 에 동일 군집화) ===
    print("\n" + "=" * 64)
    print("[4] 취약 하위유형 재현성 — 2022 군집화(k=3)")
    lab22, _, _ = cl.cluster_rested(r22, k=3)
    prof22 = cl.profile(lab22)
    prof22["유형"] = prof22["cluster"].map(cl.auto_name(prof22))
    print(prof22.to_string(index=False))

    _figures(size_df, flag_df, r22, r24, prof22)
    print("\n[compare] 완료. 그림: outputs/figures/16~18")
    return 0


def _figures(size_df, flag_df, r22, r24, prof22) -> None:
    # --- Fig 16: 쉬었음 비중 2022 vs 2024 (가중) ---
    fig, ax = plt.subplots(figsize=(6, 4.4))
    yrs = size_df["연도"].astype(str).tolist()
    vals = size_df["쉬었음_가중(%)"].tolist()
    bars = ax.bar(yrs, vals, color=[YEAR_COLORS[y] for y in size_df["연도"]], width=0.5)
    for b, v, n, pop in zip(bars, vals, size_df["표본_쉬었음"], size_df["모집단추정(명)"]):
        ax.text(b.get_x() + b.get_width() / 2, v,
                f"{v}%\n(n={n}, 약 {pop/10000:.1f}만명)", ha="center", va="bottom", fontsize=9)
    ax.set_title("쉬었음 청년 비중 — 2022 vs 2024 (가중)")
    ax.set_ylabel("청년 전체 대비 비중(%)"); ax.margins(y=0.25)
    _save(fig, "16_rested_share_2022_2024.png")

    # --- Fig 17: 내부 취약지표 보유율 2022 vs 2024 ---
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = flag_df["지표"].tolist()
    x = np.arange(len(labels)); width = 0.38
    ax.bar(x - width / 2, flag_df["2022_가중%"], width, label="2022", color=YEAR_COLORS[2022])
    ax.bar(x + width / 2, flag_df["2024_가중%"], width, label="2024", color=YEAR_COLORS[2024])
    for i, r in flag_df.iterrows():
        mark = "*" if (r["유의"] and "유의(" in str(r["유의"])) else ""
        ax.text(i, max(r["2022_가중%"], r["2024_가중%"]) + 0.5, mark,
                ha="center", fontsize=14, color="#E45756")
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("쉬었음 내 보유율(가중 %)")
    ax.set_title("쉬었음 내부 취약지표 — 2022 vs 2024  (*p<.05)")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    _save(fig, "17_rested_vuln_2022_2024.png")

    # --- Fig 18: 2022 군집 프로파일(재현성) ---
    feat_labels = list(cl.FEATURES.values())
    fig, ax = plt.subplots(figsize=(11, 5))
    xx = np.arange(len(feat_labels)); w = 0.8 / len(prof22)
    palette = {"안정형": "#4C78A8", "사회적 고립형": "#E45756", "부채압박형": "#F58518"}
    for i, (_, r) in enumerate(prof22.iterrows()):
        ax.bar(xx + i * w, [r[fl] for fl in feat_labels], w,
               label=f"{r['유형']} (n={r['표본n']})",
               color=palette.get(r["유형"], "#999"))
    ax.set_xticks(xx + w * (len(prof22) - 1) / 2); ax.set_xticklabels(feat_labels)
    ax.set_ylabel("특징 보유율(%)")
    ax.set_title("2022 쉬었음 취약 하위유형 — 군집 프로파일(재현성 확인)")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    _save(fig, "18_cluster_profile_2022.png")


if __name__ == "__main__":
    raise SystemExit(main())
