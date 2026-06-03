"""step5 보강 실험 — '가족 도움 가능'이 곧 안전은 아니다(스코프 좁히기).

쉬었음 청년을 '안전망 등급' 3단(상호배타)으로 나눠 삶 만족도를 비교한다.
  - 견고: 도움 가능 + 위험요인(부채·고립·부모비동거) 없음
  - 조건부: 도움은 가능하나 위험요인 보유  ← '도움 가능'인데도 취약할 수 있는 층
  - 취약: 도움받을 곳 없음

가설: '도움 가능'이라는 응답만으로 안전을 단정하면 안 된다(조건부<견고).
실행: python scripts/rested_safety_layers.py
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

TIERS = ["견고", "조건부", "취약"]
TIER_LABEL = {
    "견고": "견고\n(도움가능·위험요인X)",
    "조건부": "조건부\n(도움가능·위험요인O)",
    "취약": "취약\n(도움받을 곳 없음)",
}
TIER_COLOR = {"견고": "#4C78A8", "조건부": "#F58518", "취약": "#E45756"}


def _wmean(s: pd.Series, w: pd.Series) -> float:
    m = s.notna()
    return float((s[m] * w[m]).sum() / w[m].sum()) if w[m].sum() else float("nan")


def main() -> int:
    _setup_font()
    df = q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")
    for c in ["no_help_flag", "has_debt", "isolation_flag", "not_parent_cohabit",
              "life_satisfaction", "weight_person"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n = len(df)

    none = df["no_help_flag"] == 1
    risk = (df["has_debt"] == 1) | (df["isolation_flag"] == 1) | (df["not_parent_cohabit"] == 1)
    tier = pd.Series("견고", index=df.index)
    tier[~none & risk] = "조건부"
    tier[none] = "취약"
    df["tier"] = tier

    rows = []
    for t in TIERS:
        sub = df[df["tier"] == t]
        rows.append((t, len(sub), len(sub) / n * 100,
                     _wmean(sub["life_satisfaction"], sub["weight_person"])))
    res = pd.DataFrame(rows, columns=["tier", "n", "pct", "ls"])
    print(res.to_string(index=False))

    ls = {t: df.loc[df["tier"] == t, "life_satisfaction"].dropna() for t in TIERS}
    H, ph = stats.kruskal(*ls.values())
    U, pgc = stats.mannwhitneyu(ls["견고"], ls["조건부"], alternative="two-sided")
    rgc = 1 - 2 * U / (len(ls["견고"]) * len(ls["조건부"]))
    print(f"\nKruskal-Wallis(3등급): H={H:.2f}, p={ph:.4g}")
    print(f"견고 vs 조건부: p={pgc:.4g}, r={rgc:+.3f}")

    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.bar([TIER_LABEL[t] for t in TIERS], res["ls"],
                  color=[TIER_COLOR[t] for t in TIERS])
    for b, (_, r) in zip(bars, res.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, r["ls"] + 0.08,
                f"{r['ls']:.2f}\n(n={int(r['n'])}, {r['pct']:.1f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 8)
    ax.set_ylabel("삶 만족도 가중평균 (0–10)")
    sig = "유의" if ph < 0.05 else "비유의"
    ax.set_title("'가족 도움 가능'이 곧 안전은 아니다 — 안전망 등급별 삶 만족도\n"
                 f"(3등급 Kruskal-Wallis p={ph:.3f} {sig}; 단 효과는 작음)")
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.99, -0.16,
            "※ '조건부'는 도움은 가능하나 부채·고립·부모비동거 중 하나 이상 보유. "
            "도움 가능 응답만으로 안전 단정 불가(견고>조건부>취약).",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, "20_rested_safety_tiers.png")
    print("\n[safety_layers] 그림: outputs/figures/20_rested_safety_tiers.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
