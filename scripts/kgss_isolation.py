"""외부 재현·일반화 — KGSS(한국종합사회조사)로 본 '고립 vs 취업' 행복 격차.

목적(발표 연결고리):
  청년삶 데이터는 전원이 '쉬었음'이라 "고립 vs 노동시장상태 중 무엇이 웰빙을
  더 가르나"를 비교할 수 없다. KGSS(전국·독립표본)는 2021·23·25년에
  취업여부(EMPLY)·고립(BESTFRND=믿는친구 0명)·행복(HAPPINSS)이 동시에 있어
  이 비교가 가능하다.

핵심 결과:
  - 취업 여부로 가른 행복 격차 ≈ 0 (유의하지 않음)
  - 고립 여부로 가른 행복 격차는 크다(유의) → 취업보다 십수 배
  - 고립의 행복 페널티는 취업/미취업 양쪽에서 거의 동일하게 나타남
  => "쉬었음(노동시장 라벨)이 아니라 고립이 웰빙을 가른다"는 청년삶 결론을
     전국·독립표본이 재현. 정책은 일자리 연결을 넘어 '고립 해소'를 핵심 축으로.

데이터: KGSS 2003~2025 누적(DOI KOSSDA-A1-CUM-0074-V1), 성균관대 SRC / KOSSDA 소장.
가중치 FINALWT, 행복 역코딩(원 1=매우행복 → 5=매우행복).

실행: python scripts/kgss_isolation.py
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt  # noqa: E402

from scripts.insights import _setup_font, _save  # noqa: E402

YEARS = [2021, 2023, 2025]
BLUE, RED, GREY = "#4C78A8", "#E45756", "#9AA0A6"


def _load() -> tuple[pd.DataFrame, str]:
    import pyreadstat
    path = glob.glob(str(_ROOT / "data/raw/kgss/*.sav"))
    if not path:
        raise SystemExit("[kgss] data/raw/kgss/*.sav 파일이 없습니다.")
    df, _ = pyreadstat.read_sav(
        path[0], usecols=["YEAR", "AGE", "FINALWT", "HAPPINSS", "BESTFRND",
                          "EMPLY", "OTHREL4", "FEELDOWN"])
    return df, Path(path[0]).name


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df.YEAR.isin(YEARS)].copy()
    d = d[(d.HAPPINSS.between(1, 5)) & (d.BESTFRND >= 0) & (d.EMPLY.isin([1, 2]))].copy()
    d["happy"] = 6 - d.HAPPINSS          # 1~5, 높을수록 행복
    d["iso"] = (d.BESTFRND == 0).astype(int)   # 믿는 친구 0명 = 고립
    d["nonemp"] = (d.EMPLY == 2).astype(int)   # 미취업
    return d


def _wmean(d: pd.DataFrame) -> float:
    return float(np.average(d.happy, weights=d.FINALWT))


def _mwu(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    """Mann-Whitney U(비가중) p값과 |rank-biserial| 효과크기."""
    u = stats.mannwhitneyu(a, b)
    rb = 1 - 2 * u.statistic / (len(a) * len(b))
    return u.pvalue, abs(rb)


def _star(p: float) -> str:
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."


def _summ(d: pd.DataFrame, tag: str) -> dict:
    emp_hi, emp_lo = _wmean(d[d.nonemp == 0]), _wmean(d[d.nonemp == 1])
    iso_hi, iso_lo = _wmean(d[d.iso == 0]), _wmean(d[d.iso == 1])
    p_emp, rb_emp = _mwu(d[d.nonemp == 0].happy, d[d.nonemp == 1].happy)
    p_iso, rb_iso = _mwu(d[d.iso == 0].happy, d[d.iso == 1].happy)
    # 취업/미취업 군 내 고립 페널티(Δ)
    pen = {}
    for e, lab in [(0, "취업"), (1, "미취업")]:
        sub = d[d.nonemp == e]
        pen[lab] = (_wmean(sub[sub.iso == 0]) - _wmean(sub[sub.iso == 1]),
                    int((sub.iso == 1).sum()))
    print(f"\n===== {tag} (N={len(d)}) =====")
    print(f"  취업 {emp_hi:.3f} / 미취업 {emp_lo:.3f} → Δ={emp_hi-emp_lo:+.3f} "
          f"p={p_emp:.2e} {_star(p_emp)} (r={rb_emp:.3f})")
    print(f"  비고립 {iso_hi:.3f} / 고립 {iso_lo:.3f} → Δ={iso_hi-iso_lo:+.3f} "
          f"p={p_iso:.2e} {_star(p_iso)} (r={rb_iso:.3f})")
    print(f"  고립 페널티(Δ): 취업군 {pen['취업'][0]:+.3f}(n고립={pen['취업'][1]}) / "
          f"미취업군 {pen['미취업'][0]:+.3f}(n고립={pen['미취업'][1]})")
    return dict(emp_hi=emp_hi, emp_lo=emp_lo, iso_hi=iso_hi, iso_lo=iso_lo,
                d_emp=emp_hi - emp_lo, d_iso=iso_hi - iso_lo,
                p_emp=p_emp, p_iso=p_iso, rb_iso=rb_iso, pen=pen, n=len(d))


def _export_summary(s: dict,
                    fname: str = "kgss_isolation_summary.csv") -> Path:
    """앱이 읽어 표시할 핵심 수치를 CSV로 저장(하드코딩 제거용)."""
    out = _ROOT / "data" / "processed" / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "n": s["n"],
        "d_iso": round(s["d_iso"], 3),
        "d_emp": round(s["d_emp"], 3),
        "ratio": round(s["d_iso"] / max(s["d_emp"], 1e-6), 1),
        "p_iso": s["p_iso"],
        "p_emp": s["p_emp"],
        "iso_star": _star(s["p_iso"]),
        "emp_star": _star(s["p_emp"]),
        "pen_emp": round(s["pen"]["취업"][0], 3),
        "pen_nonemp": round(s["pen"]["미취업"][0], 3),
        "n_iso_emp": s["pen"]["취업"][1],
        "n_iso_nonemp": s["pen"]["미취업"][1],
    }
    pd.DataFrame([row]).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[kgss] 요약 저장: data/processed/{fname}")
    return out


def _figure(s: dict, fname: str = "24_kgss_isolation_vs_employment.png") -> None:
    _setup_font()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5),
                                   gridspec_kw={"width_ratios": [1, 1]})

    # ── 왼쪽: 무엇이 행복을 가르는가 — 격차(Δ) 막대 ──
    labels = ["취업 vs 미취업\n(노동시장 상태)", "비고립 vs 고립\n(관계·지원망)"]
    vals = [s["d_emp"], s["d_iso"]]
    cols = [GREY, RED]
    bars = axL.bar(labels, vals, color=cols, width=0.55)
    for b, v, p in zip(bars, vals, [s["p_emp"], s["p_iso"]]):
        axL.text(b.get_x() + b.get_width() / 2, v + 0.008,
                 f"Δ={v:.3f}\n{_star(p)}", ha="center", va="bottom",
                 fontsize=11, fontweight="bold",
                 color=RED if p < .05 else "#555")
    axL.axhline(0, color="#333", lw=0.8)
    axL.set_ylim(0, max(vals) * 1.35)
    axL.set_ylabel("행복 격차 Δ (5점 척도, 높을수록 큰 차이)")
    axL.set_title("취업으론 안 갈리고, '고립'으로 크게 갈린다\n"
                  f"고립 격차가 취업 격차의 약 {s['d_iso']/max(s['d_emp'],1e-6):.0f}배",
                  fontsize=11.5)
    axL.grid(axis="y", alpha=0.3)

    # ── 오른쪽: 고립 페널티는 취업/미취업 모두에서 일관 ──
    g = ["취업", "미취업"]
    pen_v = [s["pen"]["취업"][0], s["pen"]["미취업"][0]]
    bars2 = axR.bar(g, pen_v, color=[BLUE, "#B0561F"], width=0.5)
    for b, v, lab in zip(bars2, pen_v, g):
        n_iso = s["pen"][lab][1]
        axR.text(b.get_x() + b.get_width() / 2, v + 0.006,
                 f"Δ={v:.3f}\n(고립 n={n_iso})", ha="center", va="bottom",
                 fontsize=10.5, fontweight="bold", color="#333")
    axR.axhline(0, color="#333", lw=0.8)
    axR.set_ylim(0, max(pen_v) * 1.35)
    axR.set_ylabel("고립의 행복 페널티 Δ (비고립 - 고립)")
    axR.set_title("고립의 페널티는 취업·미취업 양쪽에서 거의 동일\n"
                  "= 고립 효과는 노동시장 상태와 무관하게 작동", fontsize=11.5)
    axR.grid(axis="y", alpha=0.3)

    fig.suptitle("[외부 재현·KGSS] 청년삶 결론의 전국 일반화 — "
                 "'쉬었음'이 아니라 '고립'이 웰빙을 가른다",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, -0.02,
             f"※ KGSS 2021·23·25 통합(N={s['n']:,}), 성균관대 SRC / KOSSDA 소장. "
             "가중 FINALWT, 행복=6-원점수(1~5, 높을수록 행복), 고립=믿어주는 친구 0명, "
             "Mann-Whitney U 검정. *** p<.001 / n.s. 유의하지 않음.",
             ha="center", va="top", fontsize=8.5, color="#666")
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    _save(fig, fname)
    print(f"\n[kgss] 그림 저장: outputs/figures/{fname}")


def _fig_dose_response(d: pd.DataFrame,
                       fname: str = "25_kgss_friends_doseresponse.png") -> None:
    """믿는 친구 수 구간별 가중 평균 행복 — '0명'이 절벽임을 보여주는 용량반응."""
    _setup_font()
    order = ["0명", "1-2명", "3-4명", "5명+"]

    def fb(n):
        return "0명" if n == 0 else "1-2명" if n <= 2 else "3-4명" if n <= 4 else "5명+"

    d = d.copy()
    d["fb"] = d.BESTFRND.apply(fb)
    means = [_wmean(d[d.fb == k]) for k in order]
    ns = [int((d.fb == k).sum()) for k in order]
    rho, p = stats.spearmanr(d.BESTFRND.clip(upper=10), d.happy)

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    colors = [RED, "#F2A488", "#9CC3E3", BLUE]
    bars = ax.bar(order, means, color=colors, width=0.6)
    for b, mv, n in zip(bars, means, ns):
        ax.text(b.get_x() + b.get_width() / 2, mv + 0.01,
                f"{mv:.2f}\n(n={n:,})", ha="center", va="bottom",
                fontsize=10, fontweight="bold")
    ax.annotate("'0명'(고립)에서 절벽", xy=(0, means[0]), xytext=(0.7, means[0] - 0.18),
                fontsize=10, color=RED, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_ylim(min(means) - 0.3, max(means) + 0.25)
    ax.set_ylabel("가중 평균 행복 (1~5, 높을수록 행복)")
    ax.set_title("믿는 친구가 많을수록 행복 — 특히 '0명'이 절벽\n"
                 f"단조 증가 (Spearman rho={rho:.2f}, p={p:.1e}), KGSS 2021·23·25",
                 fontsize=11.5)
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.99, -0.16, "※ KGSS 2021·23·25 통합, 가중 FINALWT. 믿어주는 친구 수 응답. "
            "3~4명 이후 완만 = 소수의 신뢰관계만 있어도 큰 차이.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, fname)
    print(f"[kgss] 그림 저장: outputs/figures/{fname}")


def _fig_convergence_2012(df: pd.DataFrame,
                          fname: str = "26_kgss_loneliness_depression_2012.png") -> None:
    """수렴증거 — 2012 외로움(OTHREL4) 단계별 우울(FEELDOWN). 다른 측정·다른 해."""
    _setup_font()
    d = df[(df.YEAR == 2012) & (df.OTHREL4.between(1, 5))
           & (df.FEELDOWN.between(1, 4))].copy()
    order = [5, 4, 3, 2, 1]   # 전혀아니다 → 매우그렇다
    labs = {5: "전혀\n아니다", 4: "별로\n아니다", 3: "보통", 2: "다소\n그렇다", 1: "매우\n그렇다"}
    dep = [float(np.average(d[d.OTHREL4 == lv].FEELDOWN,
                            weights=d[d.OTHREL4 == lv].FINALWT)) for lv in order]
    daily = [100 * np.average((d[d.OTHREL4 == lv].FEELDOWN == 4),
                              weights=d[d.OTHREL4 == lv].FINALWT) for lv in order]
    ns = [int((d.OTHREL4 == lv).sum()) for lv in order]
    hi = d[d.OTHREL4.isin([1, 2])]
    lo = d[d.OTHREL4.isin([4, 5])]
    u = stats.mannwhitneyu(hi.FEELDOWN, lo.FEELDOWN)
    rb = abs(1 - 2 * u.statistic / (len(hi) * len(lo)))

    fig, ax = plt.subplots(figsize=(8.4, 5))
    x = range(len(order))
    grad = ["#4C78A8", "#86A9CB", "#D9A39A", "#E07B6A", "#C2402E"]
    bars = ax.bar(x, dep, color=grad, width=0.62)
    for i, (b, mv, n) in enumerate(zip(bars, dep, ns)):
        ax.text(b.get_x() + b.get_width() / 2, mv + 0.02,
                f"{mv:.2f}\n(n={n})", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold")
    ax2 = ax.twinx()
    ax2.plot(x, daily, color="#7A1F12", marker="o", lw=2, ls="--",
             label="거의 매일 우울 비율")
    for i, v in enumerate(daily):
        ax2.text(i, v + 0.7, f"{v:.0f}%", ha="center", fontsize=9, color="#7A1F12")
    ax2.set_ylim(0, max(daily) * 1.5)
    ax2.set_ylabel("'거의 매일 우울' 비율 (%)", color="#7A1F12")
    ax.set_xticks(list(x))
    ax.set_xticklabels([labs[lv] for lv in order])
    ax.set_xlabel("「가까운 친구가 없어 가끔 외로움을 느낀다」 응답  →  (오른쪽일수록 외로움↑)")
    ax.set_ylim(1, max(dep) + 0.35)
    ax.set_ylabel("평균 우울감 점수 (1 전혀 ~ 4 거의매일)")
    ax.set_title("[수렴증거·KGSS 2012] 외로울수록 우울 — 다른 측정·다른 해도 같은 결론\n"
                 f"외로움 '그렇다' vs '아니다' 우울 차 유의 (MWU p={u.pvalue:.0e}, r={rb:.2f})",
                 fontsize=11.5)
    ax2.legend(loc="upper left", fontsize=9)
    ax.text(0.99, -0.2, "※ KGSS 2012, 가중 FINALWT. 친구수(2021~)와 다른 문항·다른 해인데도 "
            "외로움↑→우울↑ 동일 → 고립-웰빙 관계의 견고성.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, fname)
    print(f"[kgss] 그림 저장: outputs/figures/{fname}")


def main() -> int:
    df, fname = _load()
    print(f"[kgss] 파일: {fname}")
    d = _prep(df)
    s = _summ(d, "전국 성인 (만 18+)")
    # 청년 부분표본도 같이 점검(연결고리 강화)
    dy = d[d.AGE.between(19, 34)]
    if len(dy) > 0 and (dy.iso == 1).sum() >= 10:
        _summ(dy, "청년 부분표본 19–34")
    _export_summary(s)
    _figure(s)
    _fig_dose_response(d)
    _fig_convergence_2012(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
