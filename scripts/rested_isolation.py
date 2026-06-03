"""step5 — 쉬었음 내부 '고립'을 단일 축으로 정조준.

위험요인을 뭉치지 않고 isolation_flag(고립 경향) 하나로만 가른다.
질문: 쉬었음 내부에서 고립 여부가 (1) 웰빙(삶만족·행복감), (2) 지원망(도움없음)을 가르는가?

실행: python scripts/rested_isolation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import queries as q  # noqa: E402
from scripts.insights import _setup_font, _save  # noqa: E402

COL = {0: "#4C78A8", 1: "#E45756"}
LAB = {0: "비고립", 1: "고립 경향"}


def _wmean(s: pd.Series, w: pd.Series) -> float:
    m = s.notna()
    return float((s[m] * w[m]).sum() / w[m].sum()) if w[m].sum() else float("nan")


def main() -> int:
    _setup_font()
    df = q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")
    for c in ["isolation_flag", "no_help_flag", "life_satisfaction", "happiness",
              "subjective_class", "weight_person"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["isolation_flag"].isin([0, 1])]
    g0 = df[df["isolation_flag"] == 0]
    g1 = df[df["isolation_flag"] == 1]
    n0, n1 = len(g0), len(g1)
    print(f"비고립 n={n0}, 고립 n={n1} ({n1/(n0+n1)*100:.1f}%)")

    # 웰빙 가중평균
    for col, lab in [("life_satisfaction", "삶만족"), ("happiness", "행복감"),
                     ("subjective_class", "주관계층")]:
        m0, m1 = _wmean(g0[col], g0["weight_person"]), _wmean(g1[col], g1["weight_person"])
        a = g0[col].dropna(); b = g1[col].dropna()
        U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        r = 1 - 2 * U / (len(a) * len(b))
        print(f"  {lab}: 비고립 {m0:.2f} vs 고립 {m1:.2f} | p={p:.3g} | r={r:+.3f}")

    # 도움없음 비율(가중) + Fisher 정확검정(소표본 2x2 → 근사 없이 정확)
    nh0 = _wmean(g0["no_help_flag"], g0["weight_person"]) * 100
    nh1 = _wmean(g1["no_help_flag"], g1["weight_person"]) * 100
    ct = pd.crosstab(df["isolation_flag"], df["no_help_flag"])
    odds, pfish = stats.fisher_exact(ct)
    print(f"  도움없음: 비고립 {nh0:.1f}% vs 고립 {nh1:.1f}% | Fisher 정확검정 p={pfish:.3g}, OR={odds:.2f}")

    # --- 그림: 2패널 (웰빙 / 지원망) ---
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.8))
    wellbeing = [("life_satisfaction", "삶 만족도\n(0-10)"), ("happiness", "행복감\n(0-10)")]
    x = np.arange(len(wellbeing)); width = 0.36
    for i, gflag in enumerate([0, 1]):
        sub = df[df["isolation_flag"] == gflag]
        vals = [_wmean(sub[c], sub["weight_person"]) for c, _ in wellbeing]
        bars = axL.bar(x + i * width, vals, width, label=f"{LAB[gflag]} (n={len(sub)})",
                       color=COL[gflag])
        for b, v in zip(bars, vals):
            axL.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}",
                     ha="center", va="bottom", fontsize=9)
    axL.set_xticks(x + width / 2); axL.set_xticklabels([t for _, t in wellbeing])
    axL.set_ylim(0, 8); axL.set_ylabel("가중평균")
    pls = stats.mannwhitneyu(g0["life_satisfaction"].dropna(), g1["life_satisfaction"].dropna())[1]
    a = g0["life_satisfaction"].dropna(); b = g1["life_satisfaction"].dropna()
    rls = 1 - 2 * stats.mannwhitneyu(a, b)[0] / (len(a) * len(b))
    axL.set_title(f"고립자는 웰빙이 낮다\n(삶만족 Mann-Whitney p={pls:.1g}, r={rls:.2f} 큰 효과)")
    axL.legend(); axL.grid(axis="y", alpha=0.3)

    bars = axR.bar([LAB[0], LAB[1]], [nh0, nh1], color=[COL[0], COL[1]])
    for b, v in zip(bars, [nh0, nh1]):
        axR.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=10, fontweight="bold")
    axR.set_ylabel("도움받을 곳 '없음' 비율 (가중 %)")
    axR.set_title(f"고립자는 지원망도 약하다 (이중고)\n(Fisher 정확검정 p={pfish:.1g}, OR={odds:.1f})")
    axR.grid(axis="y", alpha=0.3); axR.margins(y=0.2)

    fig.suptitle("쉬었음 내부 '고립' 정조준 — 고립=웰빙↓ + 지원망↓ (단일 축)", fontsize=13)
    fig.tight_layout()
    _save(fig, "21_rested_isolation.png")
    print("\n[isolation] 그림: outputs/figures/21_rested_isolation.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
