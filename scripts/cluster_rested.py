"""보강분석 — 쉬었음 청년 취약 하위유형 군집화(데이터 기반).

임의 우선순위 typology(safety_net_type) 대신, 취약지표들을 함께 넣어
K-means 가 하위유형을 스스로 나누게 한다. k 는 실루엣 + 해석가능성으로 3 선택.

실행: python scripts/cluster_rested.py
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
from src import clustering as cl  # noqa: E402
from scripts.insights import _setup_font, _save  # noqa: E402

K = 3  # 실루엣은 k가 커질수록 올라가나(이항특징 특성), k=4+는 웰빙 차이 없는
       # 구조적 분할이라 해석가능성+제안서 정합성으로 3 채택.
CLUSTER_COLORS = {"안정형": "#4C78A8", "사회적 고립형": "#E45756", "부채압박형": "#F58518"}


def main() -> int:
    _setup_font()
    df = q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")
    labeled, k, scores = cl.cluster_rested(df, k=K)
    prof = cl.profile(labeled)
    names = cl.auto_name(prof)
    prof["유형"] = prof["cluster"].map(names)
    inertia_dbg = cl.inertia_by_k(df)
    print(f"[cluster] 쉬었음 {len(df):,}명 · k={k}")
    print("  실루엣:", {kk: round(v, 3) for kk, v in scores.items()})
    print("  관성(WCSS):", {kk: round(v, 0) for kk, v in inertia_dbg.items()})
    print(prof.to_string(index=False))

    # 군집 간 웰빙 차이 유의성(비가중 검정) — 고립형 소표본이라 효과크기 함께 보고
    ls = {int(c): pd.to_numeric(g["life_satisfaction"], errors="coerce").dropna()
          for c, g in labeled.dropna(subset=["cluster"]).groupby("cluster")}
    H, p = stats.kruskal(*ls.values())
    iso_c = next(c for c, n in names.items() if n == "사회적 고립형")
    iso = ls[iso_c]
    rest = pd.concat([v for c, v in ls.items() if c != iso_c])
    U, pu = stats.mannwhitneyu(iso, rest, alternative="two-sided")
    rb = 1 - 2 * U / (len(iso) * len(rest))
    print(f"\n[검정] 삶만족 3군집 Kruskal-Wallis: H={H:.2f}, p={p:.4g}")
    print(f"[검정] 고립형(n={len(iso)}) vs 나머지(n={len(rest)}): "
          f"p={pu:.4g}, rank-biserial r={rb:.3f}")

    # --- Fig 13: 군집 수 선택 — 엘보우(WCSS) + 실루엣 ---
    inertia = cl.inertia_by_k(df)
    fig, (axe, axs) = plt.subplots(1, 2, figsize=(12, 4.2))
    ki = list(inertia)
    axe.plot(ki, [inertia[i] for i in ki], marker="o", color="#4C78A8")
    axe.axvline(K, color="#E45756", ls="--", alpha=0.7)
    axe.text(K, max(inertia.values()), f" 채택 k={K}", color="#E45756", va="top")
    axe.set_title("엘보우 — 관성(WCSS)")
    axe.set_xlabel("군집 수 k"); axe.set_ylabel("관성(WCSS, 낮을수록 응집)")
    axe.set_xticks(ki); axe.grid(alpha=0.3)

    ks = list(scores)
    axs.plot(ks, [scores[i] for i in ks], marker="o", color="#54A24B")
    axs.axvline(K, color="#E45756", ls="--", alpha=0.7)
    axs.text(K, min(scores.values()), f" 채택 k={K}", color="#E45756", va="bottom")
    axs.set_title("실루엣 점수 (높을수록 분리)")
    axs.set_xlabel("군집 수 k"); axs.set_ylabel("실루엣 점수")
    axs.set_xticks(ks); axs.grid(alpha=0.3)
    fig.suptitle("군집 수 선택 근거 — 엘보우 + 실루엣", fontsize=13)
    _save(fig, "13_cluster_selection.png")

    order = prof["유형"].tolist()
    # --- Fig 14: 군집 프로파일(특징 보유율) ---
    feat_labels = list(cl.FEATURES.values())
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(feat_labels))
    width = 0.8 / len(prof)
    for i, (_, r) in enumerate(prof.iterrows()):
        vals = [r[fl] for fl in feat_labels]
        ax.bar(x + i * width, vals, width,
               label=f"{r['유형']} (n={r['표본n']})",
               color=CLUSTER_COLORS.get(r["유형"], "#999"))
    ax.set_xticks(x + width * (len(prof) - 1) / 2)
    ax.set_xticklabels(feat_labels)
    ax.set_ylabel("특징 보유율(%)")
    ax.set_title("쉬었음 청년 취약 하위유형 — 군집별 특징 프로파일")
    ax.legend(); ax.grid(axis="y", alpha=0.3)
    _save(fig, "14_cluster_profile.png")

    # --- Fig 15: 군집별 규모 + 웰빙 ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))
    colors = [CLUSTER_COLORS.get(n, "#999") for n in order]
    bars = ax1.bar(order, prof["표본n"], color=colors)
    for b, (_, r) in zip(bars, prof.iterrows()):
        ax1.text(b.get_x() + b.get_width() / 2, r["표본n"],
                 f"{r['표본n']}명\n약 {r['모집단추정(명)']/10000:.1f}만명",
                 ha="center", va="bottom", fontsize=9)
    ax1.set_title("하위유형 규모 (표본·모집단 추정)")
    ax1.set_ylabel("표본 수(명)"); ax1.margins(y=0.2)

    well = ["삶 만족도(0-10)", "행복감(0-10)"]
    xw = np.arange(len(well))
    for i, (_, r) in enumerate(prof.iterrows()):
        ax2.bar(xw + i * width, [r[w] for w in well], width,
                label=r["유형"], color=CLUSTER_COLORS.get(r["유형"], "#999"))
    ax2.set_xticks(xw + width * (len(prof) - 1) / 2)
    ax2.set_xticklabels(well)
    ax2.set_ylabel("가중 평균(0-10)")
    ax2.set_title("하위유형별 주관 웰빙")
    ax2.legend(fontsize=8); ax2.grid(axis="y", alpha=0.3)
    _save(fig, "15_cluster_outcomes.png")

    print("\n[cluster] 완료. 그림: outputs/figures/13~15")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
