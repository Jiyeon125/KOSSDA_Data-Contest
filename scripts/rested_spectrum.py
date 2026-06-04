"""step6 — 취약 '총량'(vuln_score) ↔ 웰빙: 연속 스펙트럼이 성립하는지 검정.

기대: 취약요소가 쌓일수록 웰빙이 점진 하락(스펙트럼)?
실제: 합산점수는 웰빙을 거의 설명 못 함(rho≈-0.09, 비단조) → '총량'보다 '종류(고립)'.

실행: python scripts/rested_spectrum.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import queries as q  # noqa: E402
from scripts.insights import _setup_font, _save  # noqa: E402


def _wmean(s: pd.Series, w: pd.Series) -> float:
    m = s.notna()
    return float((s[m] * w[m]).sum() / w[m].sum()) if w[m].sum() else float("nan")


def main() -> int:
    _setup_font()
    df = q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")
    for c in ["vuln_score", "life_satisfaction", "weight_person"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    scores, means, ns = [], [], []
    for s in sorted(df["vuln_score"].dropna().unique()):
        sub = df[df["vuln_score"] == s]
        scores.append(int(s))
        means.append(_wmean(sub["life_satisfaction"], sub["weight_person"]))
        ns.append(len(sub))

    d = df.dropna(subset=["vuln_score", "life_satisfaction"])
    rho, p = stats.spearmanr(d["vuln_score"], d["life_satisfaction"])
    print(f"Spearman rho={rho:.3f}, p={p:.3g}")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(scores, means, color="#72B7B2")
    for b, m, nn in zip(bars, means, ns):
        ax.text(b.get_x() + b.get_width() / 2, m + 0.05, f"{m:.2f}\n(n={nn})",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 8)
    ax.set_xlabel("취약 누적 점수 vuln_score (0~6, 취약요소 개수)")
    ax.set_ylabel("삶 만족도 가중평균 (0–10)")
    ax.set_title("취약 '총량'은 웰빙을 거의 설명 못 한다\n"
                 f"(Spearman rho={rho:.2f}, p={p:.3f} — 유의하나 사실상 무시할 수준·비단조)")
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.99, -0.18,
            "※ 점수 3 이후 표본 급감(n≤24)·만족도 반등 → 깔끔한 스펙트럼 아님. "
            "'얼마나 많이'보다 '어떤 취약(고립)'이 핵심.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, "22_rested_vuln_gradient.png")
    print("\n[spectrum] 그림: outputs/figures/22_rested_vuln_gradient.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
