"""소논문·발표용 정적 그림 — 앱에만 있던 분석을 PNG로보낸다.

실행: python scripts/paper_figures.py
산출: outputs/figures/29_type6_satisfaction.png, 30_h3_coverage.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src import queries as q  # noqa: E402
from scripts.insights import _setup_font, _save  # noqa: E402

TYPE6_ORDER = [
    "가족완충형", "금융부담형", "취약잠재형",
    "고립위험형", "대체지원형", "공공지원형",
]
TYPE6_COLORS = {
    "가족완충형": "#4C78A8", "금융부담형": "#F58518", "취약잠재형": "#9D9D9D",
    "고립위험형": "#E45756", "대체지원형": "#B279A2", "공공지원형": "#72B7B2",
}


def fig_type6_satisfaction(rested: pd.DataFrame) -> None:
    """6유형 규모·삶만족 — 소논문 §5.4·5.5."""
    r = rested.copy()
    r["safety_net_type6"] = r["safety_net_type6"].astype(str)
    prof = (
        r.groupby("safety_net_type6")
        .agg(
            인원=("safety_net_type6", "size"),
            평균_삶만족=("life_satisfaction", lambda s: pd.to_numeric(s, errors="coerce").mean()),
        )
        .reset_index()
        .rename(columns={"safety_net_type6": "유형"})
    )
    prof = prof.set_index("유형").reindex(TYPE6_ORDER).reset_index().dropna(subset=["인원"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    colors = [TYPE6_COLORS.get(t, "#999") for t in prof["유형"]]

    bars = ax1.bar(prof["유형"], prof["인원"], color=colors)
    for b, n, pct in zip(bars, prof["인원"], prof["인원"] / len(r) * 100):
        ax1.text(b.get_x() + b.get_width() / 2, n, f"{int(n)}명\n({pct:.1f}%)",
                 ha="center", va="bottom", fontsize=8)
    ax1.set_title("생활안전망 6유형 분포 (쉬었음 N=1,062)")
    ax1.set_ylabel("인원(명)")
    ax1.tick_params(axis="x", rotation=25)
    ax1.margins(y=0.2)

    bars2 = ax2.bar(prof["유형"], prof["평균_삶만족"], color=colors)
    for b, v in zip(bars2, prof["평균_삶만족"]):
        ax2.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax2.set_title("유형별 평균 삶의 만족 (0–10, 기술통계)")
    ax2.set_ylim(0, 10)
    ax2.tick_params(axis="x", rotation=25)
    ax2.axhline(6.5, color="#ccc", linestyle="--", linewidth=0.8, label="전체 평균 근처")
    ax2.margins(y=0.12)

    fig.suptitle("위험 중첩·6유형 — 고립위험형·대체지원형이 웰빙 최하위권(기술통계)", y=1.02)
    _save(fig, "29_type6_satisfaction.png")


def fig_h3_coverage(rested: pd.DataFrame) -> None:
    """H3 도달률 — 가족지원 부재 vs 전체."""
    fam = pd.to_numeric(rested.get("family_help_flag"), errors="coerce")
    no_family = rested[fam == 0]
    flag_labels = {
        "help_living_acq": "지인",
        "help_living_public": "공공기관",
        "help_living_private": "민간기관",
        "help_living_none": "도움받을 곳 없음",
    }
    cov_nf = q.coverage_rates(no_family, flag_labels)
    cov_all = q.coverage_rates(rested, flag_labels)
    cov_nf["집단"] = f"가족지원 없음 (n={len(no_family)})"
    cov_all["집단"] = "쉬었음 전체"
    cov = pd.concat([cov_all, cov_nf], ignore_index=True)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    nets = list(flag_labels.values())
    x = range(len(nets))
    width = 0.38
    palette = {"쉬었음 전체": "#9D9D9D", cov_nf["집단"].iloc[0]: "#E45756"}
    for i, grp in enumerate(["쉬었음 전체", cov_nf["집단"].iloc[0]]):
        sub = cov[cov["집단"] == grp]
        vals = [sub.loc[sub["안전망"] == n, "도달률(%)"].iloc[0] for n in nets]
        bars = ax.bar([xi + i * width for xi in x], vals, width, label=grp, color=palette[grp])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks([xi + width / 2 for xi in x])
    ax.set_xticklabels(nets)
    ax.set_ylabel("도달률(비가중 %)")
    ax.set_title("H3 · 대체 안전망 도달률 — 가족 공백을 공공이 메우지 못함")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.margins(y=0.18)
    ax.text(
        0.99, -0.2,
        "가족지원 없음 집단: '도움없음' 57.1% vs 공공 14.1% (도달률=coverage, 비가중)",
        transform=ax.transAxes, ha="right", fontsize=8, color="#666",
    )
    _save(fig, "30_h3_coverage.png")


def main() -> int:
    _setup_font()
    if not q.db_exists():
        print("[paper_figures] DB 없음 — preprocess + build_db 먼저 실행")
        return 1
    rested = q.run_query(
        f'SELECT * FROM "{q.ANALYSIS_TABLE}" WHERE is_rested=1;'
    )
    print(f"[paper_figures] 쉬었음 n={len(rested):,}")
    fig_type6_satisfaction(rested)
    fig_h3_coverage(rested)
    print("[paper_figures] 완료 → outputs/figures/29_*, 30_*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
