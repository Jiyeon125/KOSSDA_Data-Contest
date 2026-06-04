"""step1 배경 보강 — 청년 NEET 국제비교(외부 집계자료).

'쉬었음 증가'를 국제·구조 맥락에 놓는다: OECD는 청년 NEET가 줄어드는데
한국만 2014 대비 늘었고, 그중에서도 '비구직형'(구직활동 없는 쉬었음類)만 증가.

외부 참조(인용): 한국고용정보원, 「청년 니트(NEET)의 구성 변화와 노동시장
유입 촉진 방안」, 2025.05. (통계청 경제활동인구조사 원자료를 OECD 기준으로 재산출)
- 한국 청년(15~29) NEET: 2014 17.5% → 2020 20.9% → 2021 20.0% → 2022 18.3%
- OECD 평균: 2014 15.7% → 2022 12.6%  (한국은 11개국 중 2014 대비 증가한 유일국)

실행: python scripts/neet_background.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.insights import _setup_font, _save  # noqa: E402

KOR = {2014: 17.5, 2020: 20.9, 2021: 20.0, 2022: 18.3}
OECD = {2014: 15.7, 2022: 12.6}


def main() -> int:
    _setup_font()
    fig, ax = plt.subplots(figsize=(8, 4.8))

    ky = sorted(KOR)
    ax.plot(ky, [KOR[y] for y in ky], marker="o", ms=6, lw=2.2,
            color="#E45756", label="한국 (15–29세)")
    for y in ky:
        ax.text(y, KOR[y] + 0.35, f"{KOR[y]:.1f}", ha="center", fontsize=8.5,
                color="#E45756", fontweight="bold")

    oy = sorted(OECD)
    ax.plot(oy, [OECD[y] for y in oy], marker="s", ms=6, lw=2.2, ls="--",
            color="#4C78A8", label="OECD 평균")
    for y in oy:
        ax.text(y, OECD[y] - 0.7, f"{OECD[y]:.1f}", ha="center", fontsize=8.5,
                color="#4C78A8", fontweight="bold")

    ax.annotate("한국: 2014 대비 ↑ (11개국 중 유일)", xy=(2021, 20.0),
                xytext=(2016.2, 21.6), fontsize=9, color="#E45756",
                arrowprops=dict(arrowstyle="->", color="#E45756"))
    ax.annotate("OECD: 15.7 → 12.6 ↓", xy=(2022, 12.6), xytext=(2017.5, 11.0),
                fontsize=9, color="#4C78A8",
                arrowprops=dict(arrowstyle="->", color="#4C78A8"))

    ax.set_ylim(9, 23)
    ax.set_xticks(ky)
    ax.set_xlabel("연도"); ax.set_ylabel("청년 NEET 비중 (%)")
    ax.set_title("청년 NEET — OECD는 줄고 한국만 늘었다 (배경)\n"
                 "특히 '비구직형'(구직 안 하는 쉬었음類)만 증가 = 질적 고착")
    ax.legend(loc="lower left"); ax.grid(alpha=0.3)
    ax.text(0.99, -0.2, "※ 출처: 한국고용정보원(2025), 통계청 경활 원자료 OECD 기준 재산출. "
            "2022년 한국 18.3%는 OECD 11개국 중 3위.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, "00_neet_oecd_background.png")
    print("[neet] 그림 저장: outputs/figures/00_neet_oecd_background.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
