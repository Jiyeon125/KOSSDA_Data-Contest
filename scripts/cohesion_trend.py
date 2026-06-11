"""사회통합실태조사 — 청년 관계적 고립 추세 + 고립 vs 취업 웰빙 격차.

RQ-A: 청년(19~39세, d2=1·2) 관계적 고립 비율의 연간 추세
RQ-B: 청년 풀링 후 고립 vs 일자리(d6) × 행복/만족 격차 (KGSS 보조 재현)

고립 정의: 목돈·병시·우울 3문항 중 **하나라도** '없다'(코드 1) 응답.
(완전 고립=3문항 모두 '없다'는 부록으로 함께 보고)

실행: python scripts/cohesion_trend.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt  # noqa: E402

from scripts.insights import _save, _setup_font  # noqa: E402
from src.cohesion_vars import YearMap, discover_all  # noqa: E402

YOUTH_BANDS = (1, 2)   # d2: 19~29, 30대(30~39 근사 — 연령 구간 변수 한계)
NONE_CODE = 1.0          # 코드북: 1=없다 (값 레이블 확인됨)


def _load_year(m: YearMap) -> pd.DataFrame:
    cols = list({m.iso_money, m.iso_sick, m.iso_talk,
                 m.weight, m.age_band, m.employed, m.happiness, m.life_sat})
    df, _ = pyreadstat.read_sav(str(m.path), usecols=cols)
    df["year"] = m.year
    return df


def _prep(df: pd.DataFrame, m: YearMap) -> pd.DataFrame:
    d = df.copy()
    for c in (m.iso_money, m.iso_sick, m.iso_talk):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d[m.age_band].isin(YOUTH_BANDS)].copy()
    d = d[d[m.iso_money].between(1, 5) & d[m.iso_sick].between(1, 5)
          & d[m.iso_talk].between(1, 5)].copy()
    d["wt"] = pd.to_numeric(d[m.weight], errors="coerce")
    d = d[d["wt"] > 0].copy()

    d["iso_any"] = ((d[m.iso_money] == NONE_CODE)
                    | (d[m.iso_sick] == NONE_CODE)
                    | (d[m.iso_talk] == NONE_CODE)).astype(int)
    d["iso_all"] = ((d[m.iso_money] == NONE_CODE)
                    & (d[m.iso_sick] == NONE_CODE)
                    & (d[m.iso_talk] == NONE_CODE)).astype(int)

    emp = pd.to_numeric(d[m.employed], errors="coerce")
    d["employed"] = emp.map({1: 1, 2: 0})  # 1=일자리 있음, 2=없음
    d["happy"] = pd.to_numeric(d[m.happiness], errors="coerce")
    d["life_sat"] = pd.to_numeric(d[m.life_sat], errors="coerce")
    d = d[d["happy"].between(0, 10) & d["life_sat"].between(0, 10)].copy()
    return d


def _wshare(series: pd.Series, wt: pd.Series) -> float:
    return float(np.average(series, weights=wt)) * 100


def _wmean(series: pd.Series, wt: pd.Series) -> float:
    return float(np.average(series, weights=wt))


def _mwu(a: pd.Series, b: pd.Series) -> tuple[float, float]:
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    rb = abs(1 - 2 * u.statistic / (len(a) * len(b)))
    return float(u.pvalue), float(rb)


def _star(p: float) -> str:
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "n.s."


def yearly_trend(frames: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for d in frames:
        y = int(d["year"].iloc[0])
        rows.append({
            "year": y,
            "n": len(d),
            "iso_any_pct": round(_wshare(d["iso_any"], d["wt"]), 1),
            "iso_all_pct": round(_wshare(d["iso_all"], d["wt"]), 1),
            "happy_mean": round(_wmean(d["happy"], d["wt"]), 2),
        })
    return pd.DataFrame(rows).sort_values("year")


def pooled_compare(pool: pd.DataFrame) -> dict:
    sub = pool[pool["employed"].notna()].copy()
    emp = sub[sub["employed"] == 1]
    non = sub[sub["employed"] == 0]
    iso = sub[sub["iso_any"] == 1]
    niso = sub[sub["iso_any"] == 0]

    emp_hi, emp_lo = _wmean(emp["happy"], emp["wt"]), _wmean(non["happy"], non["wt"])
    iso_hi, iso_lo = _wmean(niso["happy"], niso["wt"]), _wmean(iso["happy"], iso["wt"])
    p_emp, rb_emp = _mwu(emp["happy"], non["happy"])
    p_iso, rb_iso = _mwu(niso["happy"], iso["happy"])

    pen = {}
    for e, lab in [(1, "취업"), (0, "무일자리")]:
        g = sub[sub["employed"] == e]
        pen[lab] = (_wmean(g[g["iso_any"] == 0]["happy"], g[g["iso_any"] == 0]["wt"])
                    - _wmean(g[g["iso_any"] == 1]["happy"], g[g["iso_any"] == 1]["wt"]),
                    int((g["iso_any"] == 1).sum()))

    return dict(
        n=len(sub), emp_hi=emp_hi, emp_lo=emp_lo, iso_hi=iso_hi, iso_lo=iso_lo,
        d_emp=emp_hi - emp_lo, d_iso=iso_hi - iso_lo,
        p_emp=p_emp, p_iso=p_iso, rb_emp=rb_emp, rb_iso=rb_iso, pen=pen,
        n_iso=int((sub["iso_any"] == 1).sum()),
    )


def _fig_trend(trend: pd.DataFrame, fname: str = "27_cohesion_isolation_trend.png") -> None:
    _setup_font()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(trend["year"], trend["iso_any_pct"], "o-", color="#E45756", lw=2.2,
            label="관계적 고립 (3문항 중 1개 이상 '없다')")
    ax.plot(trend["year"], trend["iso_all_pct"], "s--", color="#9AA0A6", lw=1.8,
            label="완전 고립 (3문항 모두 '없다')")
    for _, r in trend.iterrows():
        ax.annotate(f"{r['iso_any_pct']:.1f}%", (r["year"], r["iso_any_pct"]),
                    textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xlabel("조사 연도")
    ax.set_ylabel("가중 비율 (%)")
    ax.set_title("사회통합실태조사 — 청년(19~39세) 관계적 고립 비율 추세",
                 fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    ax.text(0.99, -0.14,
            f"※ KOSSDA 사회통합실태조사 {int(trend.year.min())}–{int(trend.year.max())}, "
            "청년=d2 19~29·30대(연령 구간 한계). 가중 wt1. 2011·12 제외.",
            transform=ax.transAxes, ha="right", fontsize=8, color="#666")
    fig.tight_layout()
    _save(fig, fname)


def _fig_compare(s: dict, fname: str = "28_cohesion_isolation_vs_employment.png") -> None:
    _setup_font()
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.5, 5))
    labels = ["일자리 있음 vs 없음", "비고립 vs 관계적 고립"]
    vals = [s["d_emp"], s["d_iso"]]
    cols = ["#9AA0A6", "#E45756"]
    bars = axL.bar(labels, vals, color=cols, width=0.55)
    for b, v, p in zip(bars, vals, [s["p_emp"], s["p_iso"]]):
        axL.text(b.get_x() + b.get_width() / 2, max(v, 0) + 0.02,
                 f"Δ={v:.3f}\n{_star(p)}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    axL.axhline(0, color="#333", lw=0.8)
    axL.set_ylabel("행복 격차 Δ (어제 행복, 1~10)")
    axL.set_title("청년 — 취업보다 고립이 행복을 더 가른다", fontsize=11)
    axL.grid(axis="y", alpha=0.3)

    g = ["취업", "무일자리"]
    pen_v = [s["pen"]["취업"][0], s["pen"]["무일자리"][0]]
    bars2 = axR.bar(g, pen_v, color=["#4C78A8", "#B0561F"], width=0.5)
    for b, v, lab in zip(bars2, pen_v, g):
        n_iso = s["pen"][lab][1]
        axR.text(b.get_x() + b.get_width() / 2, v + 0.02,
                 f"Δ={v:.3f}\n(고립 n={n_iso})", ha="center", fontsize=9.5)
    axR.set_ylabel("고립의 행복 페널티 Δ")
    axR.set_title("고립 페널티는 일자리 유무와 무관하게 나타남", fontsize=11)
    axR.grid(axis="y", alpha=0.3)

    ratio = s["d_iso"] / max(abs(s["d_emp"]), 1e-6)
    fig.suptitle(f"[사회통합실태조사] 청년 풀링 N={s['n']:,} — KGSS 결론의 연간·청년 재현",
                 fontsize=12, fontweight="bold")
    fig.text(0.5, -0.02,
             f"※ {s['n']:,}명(19~39세, 2013–2024 풀링), 가중 wt1. "
             f"고립=3문항 중 1개 이상 '없다'. 고립/취업 격차 비 약 {ratio:.0f}배. MWU.",
             ha="center", fontsize=8.5, color="#666")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    _save(fig, fname)


def _export_csv(trend: pd.DataFrame, summary: dict) -> None:
    proc = _ROOT / "data" / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    trend.to_csv(proc / "social_cohesion_youth_trend.csv", index=False, encoding="utf-8-sig")
    row = {k: (round(v, 4) if isinstance(v, float) else v)
             for k, v in summary.items() if k != "pen"}
    row["pen_emp"] = round(summary["pen"]["취업"][0], 3)
    row["pen_nonemp"] = round(summary["pen"]["무일자리"][0], 3)
    row["ratio"] = round(summary["d_iso"] / max(abs(summary["d_emp"]), 1e-6), 1)
    pd.DataFrame([row]).to_csv(proc / "social_cohesion_youth_summary.csv",
                               index=False, encoding="utf-8-sig")
    print(f"[cohesion] CSV: data/processed/social_cohesion_youth_*.csv")


def main() -> int:
    maps = discover_all()
    if not maps:
        print("[cohesion] 분석 가능한 연도가 없습니다. cohesion_inspect.py 먼저 실행하세요.")
        return 1

    frames = [_prep(_load_year(m), m) for m in maps]
    trend = yearly_trend(frames)
    pool = pd.concat(frames, ignore_index=True)
    summary = pooled_compare(pool)

    print("\n===== 연간 추세 (청년, 관계적 고립) =====")
    print(trend.to_string(index=False))
    print(f"\n===== 풀링 비교 (N={summary['n']:,}) =====")
    print(f"  일자리: {summary['emp_hi']:.3f} vs {summary['emp_lo']:.3f} "
          f"Δ={summary['d_emp']:+.3f} p={summary['p_emp']:.2e} {_star(summary['p_emp'])}")
    print(f"  고립:   {summary['iso_hi']:.3f} vs {summary['iso_lo']:.3f} "
          f"Δ={summary['d_iso']:+.3f} p={summary['p_iso']:.2e} {_star(summary['p_iso'])} "
          f"(r={summary['rb_iso']:.3f})")

    _fig_trend(trend)
    _fig_compare(summary)
    _export_csv(trend, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
