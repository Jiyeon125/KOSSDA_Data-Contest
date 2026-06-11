"""분석 결과의 민감도·강건성을 점검하고 요약표를 내보낸다.

실행하면 outputs/robustness_summary.md 가 생성된다.
  - 위험점수: 요인 하나씩 빼 보기(leave-one-out), 임계값 변경
  - 6유형 분류: 금융부담형↔가족완충형 우선순위 바꿔 보기
  - H1~H3 핵심 수치를 표본가중으로 다시 계산
  - 유형별 삶만족 Kruskal-Wallis + 쌍별 MWU(Holm)
  - 가족부재 집단 공적지원×부채 보조분석의 사후 검정력

실행: python scripts/robustness.py
"""

from __future__ import annotations

import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src import queries  # noqa: E402

OUT_PATH = PROJECT_ROOT / "outputs" / "robustness_summary.md"

RISK_FACTORS = {
    "부모 비동거": lambda d: (pd.to_numeric(d["live_with_parents"], errors="coerce").fillna(0) != 1),
    "가족지원 없음": lambda d: (pd.to_numeric(d["help_living_family"], errors="coerce").fillna(0) != 1),
    "도움망 없음": lambda d: (pd.to_numeric(d["help_living_none"], errors="coerce").fillna(0) == 1),
    "부채 보유": lambda d: (pd.to_numeric(d["debt_total"], errors="coerce").fillna(0) > 0),
    "이자 부담": lambda d: (pd.to_numeric(d["interest_monthly"], errors="coerce").fillna(0) > 0),
}


def weighted_median(values: pd.Series, weights: pd.Series) -> float | None:
    """가중 중앙값 (누적 가중치 50% 지점)."""
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = v.notna() & w.notna() & (w > 0)
    v, w = v[mask], w[mask]
    if v.empty:
        return None
    order = v.sort_values().index
    v, w = v.loc[order], w.loc[order]
    cum = w.cumsum() / w.sum()
    return float(v[cum >= 0.5].iloc[0])


def two_prop_power(p1: float, p2: float, n1: int, n2: int, alpha: float = 0.05) -> dict:
    """두 비율 비교의 사후 검정력(Cohen's h, 정규 근사) + 80% 검정력 필요 표본."""
    h = abs(2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2)))
    n_h = 2 * n1 * n2 / (n1 + n2)  # 조화평균 (불균형 표본 보정)
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_stat = h * math.sqrt(n_h / 2)
    power = (1 - stats.norm.cdf(z_a - z_stat)) + stats.norm.cdf(-z_a - z_stat)
    n_req = ((z_a + stats.norm.ppf(0.80)) / h) ** 2 if h > 0 else float("inf")
    return {"h": round(h, 3), "power": round(float(power), 3), "n_per_group_80": int(math.ceil(n_req))}


def main() -> int:
    if not queries.db_exists():
        print("[robustness] DB가 없습니다. 먼저 전처리/적재를 실행하세요.")
        return 1

    df = queries.run_query(f'SELECT * FROM "{queries.ANALYSIS_TABLE}";')
    r = df[df["is_rested"] == 1].copy()
    n = len(r)
    lines: list[str] = [
        "# 강건성 점검 결과 (robustness checks)",
        "",
        f"> scripts/robustness.py 산출 · 쉬었음 N={n:,} (청년삶 2024)",
        "",
    ]

    # ------------------------------------------------------------------
    # 1) 위험점수 민감도 — leave-one-out + 임계값
    # ------------------------------------------------------------------
    flags = {name: fn(r).astype(int) for name, fn in RISK_FACTORS.items()}
    full_score = sum(flags.values())
    base_pct = float((full_score >= 2).mean() * 100)

    lines += ["## 1. 위험점수 민감도 (leave-one-out)", "",
              f"- 기준: 5요인 전체, 위험군(점수≥2) = **{base_pct:.1f}%**", "",
              "| 제외한 요인 | 남은 4요인 위험군(≥2) 비율 | 기준 대비 |", "|---|---|---|"]
    loo = []
    for name in RISK_FACTORS:
        score4 = full_score - flags[name]
        pct = float((score4 >= 2).mean() * 100)
        loo.append(pct)
        lines.append(f"| {name} | {pct:.1f}% | {pct - base_pct:+.1f}%p |")
    lines += ["",
              f"- 4요인 위험군 비율 범위: **{min(loo):.1f}% ~ {max(loo):.1f}%**", ""]

    thr_rows = []
    for thr in (1, 2, 3):
        thr_rows.append(f"| 점수 ≥ {thr} | {float((full_score >= thr).mean() * 100):.1f}% |")
    lines += ["### 임계값 변경", "", "| 위험군 정의 | 비율 |", "|---|---|", *thr_rows, ""]

    # ------------------------------------------------------------------
    # 2) 6유형 우선순위 민감도 — 금융부담형 ↔ 가족완충형 스왑
    # ------------------------------------------------------------------
    f0 = lambda c: pd.to_numeric(r[c], errors="coerce").fillna(0)  # noqa: E731
    parent = f0("live_with_parents").eq(1)
    family = f0("help_living_family").eq(1)
    none_h = f0("help_living_none").eq(1)
    fin = f0("debt_total").gt(0) | f0("interest_monthly").gt(0) | f0("debt_living").gt(0)
    pub = f0("help_living_public").eq(1)
    alt = f0("help_living_acq").eq(1) | f0("help_living_private").eq(1)

    def classify(priority_fin_first: bool) -> pd.Series:
        t = pd.Series("취약잠재형", index=r.index, dtype="object")
        t[alt] = "대체지원형"
        t[pub] = "공공지원형"
        if priority_fin_first:  # 원 규칙: 금융 > 가족
            t[family & parent] = "가족완충형"
            t[fin] = "금융부담형"
        else:  # 스왑: 가족 > 금융
            t[fin] = "금융부담형"
            t[family & parent] = "가족완충형"
        t[none_h] = "고립위험형"
        return t

    orig = classify(True).value_counts()
    swap = classify(False).value_counts()
    lines += ["## 2. 6유형 우선순위 민감도 (금융부담형 ↔ 가족완충형 스왑)", "",
              "| 유형 | 원 규칙(금융 우선) | 스왑(가족 우선) | 변화 |", "|---|---|---|---|"]
    for t in ["고립위험형", "금융부담형", "가족완충형", "공공지원형", "대체지원형", "취약잠재형"]:
        o, s = int(orig.get(t, 0)), int(swap.get(t, 0))
        lines.append(f"| {t} | {o} ({o/n*100:.1f}%) | {s} ({s/n*100:.1f}%) | {s-o:+d} |")
    lines += ["", "- 고립위험형·공공지원형·대체지원형·취약잠재형은 규칙 스왑의 영향을 받지 않음(정의상 동일).", ""]

    # ------------------------------------------------------------------
    # 3) 가중 강건성 — 핵심 수치 가중 재산출
    # ------------------------------------------------------------------
    r["_parent"] = np.where(f0("live_with_parents").eq(1), "부모동거", "비동거")
    lines += ["## 3. 가중 강건성 (핵심 수치의 가중 재산출)", "",
              "| 지표 | 비가중(보고값) | 가중 | 방향 유지 |", "|---|---|---|---|"]

    rows = []
    for g in ("부모동거", "비동거"):
        sub = r[r["_parent"] == g]
        uw = float((pd.to_numeric(sub["debt_total"], errors="coerce").fillna(0) > 0).mean() * 100)
        wt = queries.weighted_share(sub, "has_debt")["비율_가중(%)"]
        rows.append((g, uw, wt))
    ok = (rows[1][1] > rows[0][1]) and (rows[1][2] > rows[0][2])
    lines.append(f"| H1 부채 보유율 (동거 vs 비동거) | {rows[0][1]:.1f}% vs {rows[1][1]:.1f}% | "
                 f"{rows[0][2]}% vs {rows[1][2]}% | {'예' if ok else '**아니오**'} |")

    fam0 = r[f0("help_living_family").eq(0)]
    uw_none = float((pd.to_numeric(fam0["help_living_none"], errors="coerce") == 1).mean() * 100)
    wt_none = queries.weighted_share(fam0, "no_help_flag")["비율_가중(%)"]
    lines.append(f"| H3 가족부재 집단 '도움없음' | {uw_none:.1f}% | {wt_none}% | "
                 f"{'예' if (wt_none or 0) > 30 else '**아니오**'} |")

    med_rows = []
    for g, lab in ((1, "가족 도움 가능"), (0, "가족 도움 없음")):
        sub = r[f0("help_living_family").eq(g)]
        uw = float(pd.to_numeric(sub["living_cost"], errors="coerce").median())
        wm = weighted_median(sub["living_cost"], sub[queries.WEIGHT_COL])
        med_rows.append((lab, uw, wm))
    ok2 = med_rows[0][1] > med_rows[1][1] and (med_rows[0][2] or 0) > (med_rows[1][2] or 0)
    lines.append(f"| H2 월 생활비 중앙값 (가족有 vs 無) | {med_rows[0][1]:.0f} vs {med_rows[1][1]:.0f} | "
                 f"{med_rows[0][2]:.0f} vs {med_rows[1][2]:.0f} | {'예' if ok2 else '**아니오**'} |")
    lines.append("")

    # ------------------------------------------------------------------
    # 4) 6유형 × 삶만족 — Kruskal-Wallis + 쌍별 MWU(Holm)
    # ------------------------------------------------------------------
    sat = pd.to_numeric(r["life_satisfaction"], errors="coerce")
    groups, labels = [], []
    for t, sub in r.groupby("safety_net_type6"):
        s = pd.to_numeric(sub["life_satisfaction"], errors="coerce").dropna()
        if len(s) >= 10:  # 소표본 유형(예: 공공지원형 n=14는 포함, n<10 제외)
            groups.append(s)
            labels.append(t)
    kw_h, kw_p = stats.kruskal(*groups)
    lines += ["## 4. 6유형 × 삶만족 — 전체 검정 + 사후검정", "",
              f"- **Kruskal-Wallis**: H={kw_h:.1f}, p={kw_p:.3g} "
              f"({'유의' if kw_p < 0.05 else '비유의'}) — 유형 간 삶만족 분포 차이",
              "", "| 쌍 | 중앙값 | MWU p(원) | p(Holm) | 유의 |", "|---|---|---|---|---|"]

    pairs, pvals = [], []
    for (i, a), (j, b) in combinations(enumerate(labels), 2):
        u, p = stats.mannwhitneyu(groups[i], groups[j], alternative="two-sided")
        pairs.append((a, b, float(groups[i].median()), float(groups[j].median()), p))
        pvals.append(p)
    order = np.argsort(pvals)
    holm = {}
    m = len(pvals)
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = min(1.0, (m - rank) * pvals[idx])
        running_max = max(running_max, adj)
        holm[idx] = running_max
    for idx, (a, b, ma, mb, p) in enumerate(pairs):
        sig = "✅" if holm[idx] < 0.05 else "—"
        lines.append(f"| {a} vs {b} | {ma:.1f} vs {mb:.1f} | {p:.3g} | {holm[idx]:.3g} | {sig} |")
    lines += ["", "- 쌍별 비교는 Holm 보정 p<.05 기준. 공공지원형(n=14)은 검정력 한계로 해석 주의.", ""]

    # ------------------------------------------------------------------
    # 5) 검정력 실계산 — 소논문 5.3 보조분석 (가족부재 집단 공적지원×부채)
    # ------------------------------------------------------------------
    pub_in_fam0 = pd.to_numeric(fam0["has_public_transfer"], errors="coerce").fillna(0)
    g_no = fam0[pub_in_fam0 == 0]
    g_yes = fam0[pub_in_fam0 == 1]
    p_no = float((pd.to_numeric(g_no["debt_total"], errors="coerce").fillna(0) > 0).mean())
    p_yes = float((pd.to_numeric(g_yes["debt_total"], errors="coerce").fillna(0) > 0).mean())
    pw = two_prop_power(p_no, p_yes, len(g_no), len(g_yes))
    lines += ["## 5. 사후 검정력 (가족부재 집단, 공적지원×부채)", "",
              f"- 가족부재 집단 내 공적지원 미보유 vs 보유의 부채 보유율: "
              f"{p_no*100:.1f}% (n={len(g_no)}) vs {p_yes*100:.1f}% (n={len(g_yes)})",
              f"- **Cohen's h = {pw['h']}**, 현재 표본의 사후 검정력 = **{pw['power']*100:.0f}%** (α=.05 양측)",
              f"- 검정력 80% 달성에 필요한 표본 ≈ **집단당 {pw['n_per_group_80']}명**",
              "- 유의하지 않음은 '차이 없음'이 아니라, 표본이 작아 판별이 어렵다는 뜻으로 해석.", ""]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[robustness] 저장 완료 -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
