"""심화분석(B): 쉬었음 청년 '내부'의 생활안전망 격차.

제안서 핵심 흐름:
  쉬어도 생활비는 필요 → 무엇으로 버티나 → 다수는 가족지원망, 일부는 도움없음/부채의존
  → 쉬었음 내부의 생활안전망 격차를 본다.

원칙(가중치 both):
  - 비율/평균/규모 = 가중(weight_person, 모집단 대표 추정)
  - 유의성 검정 n/p = 비가중 (가중합으로 인한 거짓 유의 방지)
  - 소표본(공식 n=45 등) 셀은 검정 대신 기술통계 + 한계 명시

실행: python scripts/rested_gap.py
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

NET_ORDER = ["비공식(가족·지인)", "공식(공공·민간)", "없음"]
NET_COLORS = {"비공식(가족·지인)": "#4C78A8", "공식(공공·민간)": "#F58518", "없음": "#E45756"}

# 외부 결과지표(취약점수 구성요소가 아니므로 격차 해석에 안전)
MEAN_OUTCOMES = {"life_satisfaction": "삶 만족도(0-10)", "happiness": "행복감(0-10)",
                 "subjective_class": "주관적 계층(1-5)"}
RATE_OUTCOMES = {"isolation_flag": "고립 경향", "has_debt": "부채 보유",
                 "has_interest": "이자 부담"}


def _load_rested() -> pd.DataFrame:
    return q.run_query("SELECT * FROM youth_life_2024_analysis WHERE is_rested=1")


def fig_typology(df: pd.DataFrame) -> pd.DataFrame:
    """생활안전망 유형 분포 (표본수 + 가중 모집단 추정)."""
    share = q.weighted_group_share(df, "safety_net_type")
    share["_o"] = share["집단"].map({g: i for i, g in enumerate(NET_ORDER)})
    share = share.sort_values("_o")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(share["집단"], share["비율_가중(%)"],
                  color=[NET_COLORS.get(g, "#999") for g in share["집단"]])
    for b, (_, r) in zip(bars, share.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, r["비율_가중(%)"],
                f"{r['비율_가중(%)']}%\n(표본 {r['표본n']}명\n약 {r['모집단추정(명)']/10000:.1f}만명)",
                ha="center", va="bottom", fontsize=9)
    ax.set_title("쉬었음 청년의 생활안전망 유형 (가중 비율·모집단 추정)")
    ax.set_ylabel("비율(%)")
    ax.margins(y=0.25)
    _save(fig, "10_rested_safetynet_typology.png")
    return share


def fig_gap_by_type(df: pd.DataFrame) -> None:
    """생활안전망 유형별 결과 격차 (가중 평균 + 가중 비율)."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))

    # 평균 지표
    ax = axes[0]
    x = range(len(MEAN_OUTCOMES))
    width = 0.25
    for i, g in enumerate(NET_ORDER):
        sub = df[df["safety_net_type"] == g]
        vals = [q.weighted_mean(sub, c) for c in MEAN_OUTCOMES]
        ax.bar([xi + i * width for xi in x], vals, width, label=g, color=NET_COLORS[g])
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(list(MEAN_OUTCOMES.values()), rotation=10)
    ax.set_title("유형별 주관 웰빙 (가중 평균)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    # 비율 지표
    ax = axes[1]
    x = range(len(RATE_OUTCOMES))
    for i, g in enumerate(NET_ORDER):
        sub = df[df["safety_net_type"] == g]
        vals = [q.weighted_share(sub, c)["비율_가중(%)"] for c in RATE_OUTCOMES]
        ax.bar([xi + i * width for xi in x], vals, width, label=g, color=NET_COLORS[g])
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(list(RATE_OUTCOMES.values()))
    ax.set_ylabel("비율(%)")
    ax.set_title("유형별 취약 지표 (가중 비율)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("쉬었음 청년 내부: 생활안전망 유형별 격차", y=1.02)
    _save(fig, "11_rested_gap_by_type.png")


def fig_vuln_spectrum(df: pd.DataFrame) -> None:
    """취약 누적(vuln_score) 스펙트럼 + 고/저취약 외부지표 격차."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.6))

    vc = pd.to_numeric(df["vuln_score"], errors="coerce").value_counts().sort_index()
    ax1.bar(vc.index.astype(int), vc.values, color="#72B7B2")
    for xi, v in zip(vc.index.astype(int), vc.values):
        ax1.text(xi, v, str(int(v)), ha="center", va="bottom", fontsize=9)
    ax1.set_title("취약 누적 점수 분포 (쉬었음 내부, 0~6)")
    ax1.set_xlabel("vuln_score (취약요소 개수)")
    ax1.set_ylabel("표본 수(명)")

    df = df.copy()
    df["hi"] = (pd.to_numeric(df["vuln_score"], errors="coerce") >= 3)
    grp = {True: "고취약(3점+)", False: "저취약(0-2)"}
    x = range(len(MEAN_OUTCOMES))
    width = 0.35
    for i, key in enumerate([False, True]):
        sub = df[df["hi"] == key]
        vals = [q.weighted_mean(sub, c) for c in MEAN_OUTCOMES]
        ax2.bar([xi + i * width for xi in x], vals, width, label=grp[key],
                color="#9D9D9D" if not key else "#E45756")
    ax2.set_xticks([xi + width / 2 for xi in x])
    ax2.set_xticklabels(list(MEAN_OUTCOMES.values()), rotation=10)
    ax2.set_title("고/저취약 주관 웰빙 (가중 평균)")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("쉬었음 청년 내부: 취약 누적 스펙트럼", y=1.02)
    _save(fig, "12_rested_vuln_spectrum.png")


def _report(df: pd.DataFrame) -> None:
    print("\n===== 쉬었음 내부 생활안전망 격차 (가중 기술 + 비가중 검정) =====")
    print("\n[유형 분포]")
    print(q.weighted_group_share(df, "safety_net_type").to_string(index=False))

    print("\n[핵심 대비: '없음'(취약) vs '비공식'(가족·지인)] — 검정은 비가중 n")
    for col, label in {**MEAN_OUTCOMES}.items():
        r = q.mann_whitney_compare(df, "safety_net_type", col, "없음", "비공식(가족·지인)")
        if r["p"] is None:
            continue
        wm_a = q.weighted_mean(df[df["safety_net_type"] == "없음"], col)
        wm_b = q.weighted_mean(df[df["safety_net_type"] == "비공식(가족·지인)"], col)
        print(f"  - {label:14s}: 가중평균 없음 {wm_a} vs 비공식 {wm_b} | "
              f"p={r['p']:.3g} {r['유의']} | r={r['효과크기r']}({r['효과해석']})")
    for col, label in RATE_OUTCOMES.items():
        r = q.chi_square_compare(df, "safety_net_type", col, "없음", "비공식(가족·지인)")
        if r.get("p") is None:
            continue
        sa = q.weighted_share(df[df["safety_net_type"] == "없음"], col)
        sb = q.weighted_share(df[df["safety_net_type"] == "비공식(가족·지인)"], col)
        warn = f" *{r.get('경고')}" if r.get("경고") else ""
        print(f"  - {label:14s}: 가중비율 없음 {sa['비율_가중(%)']}% vs 비공식 {sb['비율_가중(%)']}% | "
              f"p={r['p']:.3g} {r['유의']} | V={r['효과크기V']}{warn}")

    print("\n[고취약(3점+) vs 저취약(0-2)] 외부지표 — 검정은 비가중 n")
    df = df.copy()
    df["hi"] = (pd.to_numeric(df["vuln_score"], errors="coerce") >= 3).map({True: "고취약", False: "저취약"})
    n_hi = int((df["hi"] == "고취약").sum())
    print(f"  (고취약 n={n_hi}, 저취약 n={len(df)-n_hi})")
    for col, label in {**MEAN_OUTCOMES, "future_feasibility": "미래전망(1-3)"}.items():
        r = q.mann_whitney_compare(df, "hi", col, "고취약", "저취약")
        if r["p"] is None:
            continue
        print(f"  - {label:14s}: 중앙값 고 {r['중앙값_A']} vs 저 {r['중앙값_B']} | "
              f"p={r['p']:.3g} {r['유의']} | r={r['효과크기r']}({r['효과해석']})")
    r = q.chi_square_compare(df, "hi", "isolation_flag", "고취약", "저취약")
    if r.get("p") is not None:
        warn = f" *{r.get('경고')}" if r.get("경고") else ""
        print(f"  - {'고립 경향':14s}: p={r['p']:.3g} {r['유의']} | V={r['효과크기V']}{warn}")


def main() -> int:
    _setup_font()
    if not q.db_exists():
        print("[rested_gap] DB가 없습니다.")
        return 1
    df = _load_rested()
    print(f"[rested_gap] 쉬었음 청년 {len(df):,}명 로드")
    fig_typology(df)
    fig_gap_by_type(df)
    fig_vuln_spectrum(df)
    _report(df)
    print("\n[rested_gap] 완료. 그림: outputs/figures/10~12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
