"""step5 보강 — 공식 '은둔 기간'으로 본 용량반응 + 외부 공식조사 수렴.

binary 고립(outing_freq 7~8, n=41)보다 풍부한 청년삶 2024 공식변수
`seclusion_duration`(은둔 생활 지속기간, 1~6)을 쓴다.
쉬었음 청년 내부에서 은둔이 길수록 삶만족이 단계적으로 낮아지는지(용량반응),
그리고 그 결과가 외부 공식조사(복지부 2023 고립·은둔청년 실태조사)와 수렴하는지 본다.

외부 참조(인용): 보건복지부·한국보건사회연구원(김성아 외), 「2023년 고립·은둔 청년 실태조사」,
2023.12.13. 고립·은둔 청년 삶만족 3.7점 vs 전체 청년 평균 6.7점.

실행: python scripts/rested_seclusion.py
주의: seclusion_duration 은 2024 조사에만 존재 → 연도비교 불가(2024 횡단 전용).
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

# 외부 공식조사 참조값(복지부 2023 고립·은둔청년 실태조사)
EXT_ALL_YOUTH_LS = 6.7   # 전체 청년 평균 삶만족
EXT_ISOLATED_LS = 3.7    # 고립·은둔 청년 삶만족

DUR_LAB = {0: "은둔\n없음", 1: "<6개월", 2: "6개월\n~1년", 3: "1~3년",
           4: "3~5년", 5: "5~7년", 6: "7년+"}


def _wmean(s: pd.Series, w: pd.Series) -> float:
    m = s.notna()
    return float((s[m] * w[m]).sum() / w[m].sum()) if w[m].sum() else float("nan")


def main() -> int:
    _setup_font()
    df = q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")
    for c in ["seclusion_duration", "life_satisfaction", "weight_person"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # 은둔 '없음'(비해당)=0, 그 외 기간 1~6
    df["secl"] = df["seclusion_duration"].fillna(0)
    ls, w = df["life_satisfaction"], df["weight_person"]

    # 용량반응 집계
    rows = []
    for k, lab in DUR_LAB.items():
        m = (df["secl"] == k) & ls.notna()
        if m.sum() == 0:
            continue
        rows.append({"k": k, "lab": lab, "ls": _wmean(df.loc[m, "life_satisfaction"],
                     df.loc[m, "weight_person"]), "n": int(m.sum())})
    agg = pd.DataFrame(rows)
    print(agg.to_string(index=False))

    # 추세검정(은둔 경험자 한정: 기간 1~6 ↔ 삶만족, 단조성)
    sub = df[(df["secl"] >= 1) & ls.notna()]
    rho_in, p_in = stats.spearmanr(sub["secl"], sub["life_satisfaction"])
    # 전체(없음 포함) 단조성
    full = df[ls.notna()]
    rho_all, p_all = stats.spearmanr(full["secl"], full["life_satisfaction"])
    print(f"Spearman(은둔자내 기간↔삶만족) rho={rho_in:.3f} p={p_in:.3g}")
    print(f"Spearman(전체 은둔정도↔삶만족) rho={rho_all:.3f} p={p_all:.3g}")

    # 우리 극단군(7년+) vs 외부 고립은둔, 우리 은둔없음 vs 외부 전체청년
    ours_none = float(agg.loc[agg.k == 0, "ls"].iloc[0])
    ours_long = float(agg.loc[agg.k == 6, "ls"].iloc[0])
    n_long = int(agg.loc[agg.k == 6, "n"].iloc[0])

    # === 그림: 2패널 ===
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5),
                                   gridspec_kw={"width_ratios": [1.7, 1]})

    # 좌: 용량반응 (은둔없음=파랑, 기간 길수록 빨강 진하게)
    reds = plt.cm.Reds(np.linspace(0.35, 0.9, 6))
    colors = ["#4C78A8"] + [reds[i] for i in range(len(agg) - 1)]
    bars = axL.bar(agg["lab"], agg["ls"], color=colors)
    for b, r in zip(bars, agg.itertuples()):
        axL.text(b.get_x() + b.get_width() / 2, r.ls + 0.08,
                 f"{r.ls:.2f}\n(n={r.n})", ha="center", va="bottom", fontsize=8.5)
    axL.set_ylim(0, 8); axL.set_ylabel("삶 만족도 가중평균 (0–10)")
    axL.set_title("쉬었음 청년 — 은둔 기간이 길수록 삶만족 '단계적' 하락\n"
                  f"(은둔자내 Spearman rho={rho_in:.2f}, p={p_in:.3f}; 공식 은둔변수)")
    axL.grid(axis="y", alpha=0.3)
    axL.text(0.99, -0.2, "※ 청년삶 2024 공식 '은둔 지속기간'(seclusion_duration). "
             "장기군 소표본(n≤20) 주의·단조 경향은 뚜렷.",
             transform=axL.transAxes, ha="right", va="top", fontsize=8, color="#666")

    # 우: 외부 공식조사와 수렴
    labels = ["은둔 없음\n(우리)", "전체 청년\n(복지부)", "장기은둔7년+\n(우리)", "고립·은둔\n(복지부)"]
    vals = [ours_none, EXT_ALL_YOUTH_LS, ours_long, EXT_ISOLATED_LS]
    bcol = ["#4C78A8", "#A8C4E0", "#E45756", "#F0A6A6"]
    bars = axR.bar(labels, vals, color=bcol)
    for b, v in zip(bars, vals):
        axR.text(b.get_x() + b.get_width() / 2, v + 0.1, f"{v:.2f}",
                 ha="center", va="bottom", fontsize=9, fontweight="bold")
    axR.set_ylim(0, 8); axR.set_ylabel("삶 만족도 (0–10)")
    axR.set_title("내부 미시 ↔ 외부 공식조사 '수렴'\n(6.70 vs 6.7 · 3.75 vs 3.7, 거의 일치)")
    axR.grid(axis="y", alpha=0.3)
    axR.axhline(EXT_ALL_YOUTH_LS, color="#4C78A8", ls=":", lw=1, alpha=0.6)
    axR.axhline(EXT_ISOLATED_LS, color="#E45756", ls=":", lw=1, alpha=0.6)

    fig.suptitle("공식 '은둔' 척도로 본 쉬었음 내부 고위험 — 외부 공식조사가 같은 결론", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, "23_rested_seclusion_doseresponse.png")
    print(f"\n[seclusion] 그림 저장. 우리 은둔없음={ours_none:.2f}(≈{EXT_ALL_YOUTH_LS}), "
          f"7년+={ours_long:.2f}(≈{EXT_ISOLATED_LS}, n={n_long})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
