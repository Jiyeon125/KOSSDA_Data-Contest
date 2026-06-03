"""전처리 결과에서 인사이트를 뽑기 위한 경량 분석 + 시각화 스크립트.

- SQLite(youth_life_2024_analysis, eaps_labor_status_summary)에서 데이터를 읽어
  공모전 배경/본분석/집단비교용 그림을 outputs/figures 에 저장한다.
- 집단 비교는 비모수 검정(Mann-Whitney)·카이제곱 + 효과크기를 함께 출력한다.

실행:
    python scripts/insights.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src import queries as q  # noqa: E402

FIG_DIR = _PROJECT_ROOT / "outputs" / "figures"

# 4개 노동상태 집단 (분석 순서 고정) + 색상
GROUP_ORDER = ["취업자", "실업자", "쉬었음", "비경활(기타)"]
GROUP_COLORS = {"취업자": "#4C78A8", "실업자": "#F58518", "쉬었음": "#E45756", "비경활(기타)": "#9D9D9D"}


def _setup_font() -> None:
    """한글이 깨지지 않도록 폰트를 설정한다(Windows 기본: Malgun Gothic)."""
    for name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
        try:
            plt.rcParams["font.family"] = name
            break
        except Exception:  # noqa: BLE001
            continue
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120


def _add_group_en(df: pd.DataFrame) -> pd.DataFrame:
    """labor_group 의 한글 인코딩에 의존하지 않도록 플래그로 표준 라벨을 만든다."""
    def label(row):
        if row["is_employed"] == 1:
            return "취업자"
        if row["is_unemployed"] == 1:
            return "실업자"
        if row["is_rested"] == 1:
            return "쉬었음"
        return "비경활(기타)"

    out = df.copy()
    out["group"] = out.apply(label, axis=1)
    return out


def _save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [그림] 저장: {path.relative_to(_PROJECT_ROOT).as_posix()}")
    return path


# ----------------------------------------------------------------------
# EAPS 배경 추이
# ----------------------------------------------------------------------
def fig_eaps_trends(eaps: pd.DataFrame) -> None:
    rested = eaps[eaps["indicator"] == "쉬었음"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    # '계'(전 연령 합계)는 40·50·60대까지 포함해 청년 분석을 가려 제외.
    # 청년삶 타깃(19~34)은 아래 두 밴드(15-29 · 30-39) 사이에 위치.
    bands = {"15 - 29세": "#4C78A8", "30 - 39세": "#54A24B"}
    for age, color in bands.items():
        sub = rested[rested["age_group"] == age].sort_values("year")
        if sub.empty:
            continue
        ax.plot(sub["year"], sub["value"], marker="o", ms=3, label=age, color=color)
    ax.set_title("청년·30대 '쉬었음' 인구 추이 (EAPS, 천 명)")
    ax.set_xlabel("연도")
    ax.set_ylabel("쉬었음 인구 (천 명)")
    ax.legend(title="연령대")
    ax.grid(alpha=0.3)
    ax.text(0.99, -0.18, "※ 전 연령 합계(계)는 40·50·60대 포함이라 청년 분석에서 제외",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, "01_eaps_rested_trend.png")

    # 청년 실업률 vs 쉬었음 — 같은 연령(15-29)·기간, 단위가 달라 2단 패널로 대비
    rate = eaps[eaps["indicator"].str.contains("실업률", na=False)]
    u = rate[rate["age_group"] == "15 - 29세"].sort_values("year")
    r = rested[rested["age_group"] == "15 - 29세"].sort_values("year")
    fig, (axt, axb) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axt.plot(u["year"], u["value"], marker="o", ms=3, color="#F58518")
    axt.set_title("청년(15-29) 실업률 — 등락 후 최근 오히려 하락", color="#F58518")
    axt.set_ylabel("실업률 (%)")
    axt.grid(alpha=0.3)
    axb.plot(r["year"], r["value"], marker="o", ms=3, color="#4C78A8")
    axb.set_title("청년(15-29) '쉬었음' 인구 — 추세적 증가", color="#4C78A8")
    axb.set_ylabel("쉬었음 (천 명)")
    axb.set_xlabel("연도")
    axb.grid(alpha=0.3)
    fig.suptitle("같은 청년, 같은 기간 — 실업률은 하락하는데 '쉬었음'은 증가", fontsize=13)
    _save(fig, "02_eaps_unemp_rate.png")


def fig_youth_unemp_vs_rested(eaps: pd.DataFrame) -> None:
    """청년(15-29) 실업률(%) ↓ vs '쉬었음' 인구(천명) ↑ 대비.

    단위가 다른 두 지표라 이중축(혼란) 대신 **상하 2단(축 공유 X)** 으로 그린다.
    핵심 메시지: 실업률이 좋아져도 '쉬었음'은 늘어 → 실업통계 밖 사각지대.
    """
    yr_min = 2003
    rate = eaps[(eaps["indicator"].str.contains("실업률", na=False))
                & (eaps["age_group"] == "15 - 29세")
                & (eaps["year"] >= yr_min)].sort_values("year")
    rested = eaps[(eaps["indicator"] == "쉬었음")
                  & (eaps["age_group"] == "15 - 29세")
                  & (eaps["year"] >= yr_min)].sort_values("year")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.5, 6), sharex=True)
    a1.plot(rate["year"], rate["value"], marker="o", ms=3, color="#F58518")
    a1.set_ylabel("청년 실업률 (%)", color="#F58518")
    a1.set_title("① 청년(15-29) 실업률 — 2017년 정점 후 하락(표면상 개선)", fontsize=11)
    a1.grid(alpha=0.3)
    if not rate.empty:
        rmax = rate.loc[rate["value"].idxmax()]
        rend = rate.iloc[-1]
        a1.annotate(f"{rmax['value']:.1f}%", (rmax["year"], rmax["value"]),
                    textcoords="offset points", xytext=(0, -14), ha="center",
                    color="#F58518", fontsize=9, fontweight="bold")
        a1.annotate(f"{rend['value']:.1f}%", (rend["year"], rend["value"]),
                    textcoords="offset points", xytext=(0, 8), ha="center",
                    color="#F58518", fontsize=9, fontweight="bold")
        a1.margins(y=0.18)

    a2.plot(rested["year"], rested["value"], marker="o", ms=3, color="#4C78A8")
    a2.set_ylabel("청년 쉬었음 (천명)", color="#4C78A8")
    a2.set_title("② 그런데 '쉬었음' 인구는 증가 — 노동시장 밖으로 이탈", fontsize=11)
    a2.set_xlabel("연도")
    a2.grid(alpha=0.3)
    if not rested.empty:
        send = rested.iloc[-1]
        a2.annotate(f"{send['value']:.0f}천", (send["year"], send["value"]),
                    textcoords="offset points", xytext=(0, 8), ha="center",
                    color="#4C78A8", fontsize=9, fontweight="bold")
    fig.suptitle("실업률 ↓ 인데 쉬었음 ↑ — 실업통계로는 안 잡히는 청년 사각지대", fontsize=13)
    fig.tight_layout()
    _save(fig, "02b_youth_unemp_vs_rested.png")


# ----------------------------------------------------------------------
# 청년삶 2024: 집단 개요
# ----------------------------------------------------------------------
def fig_group_overview(df: pd.DataFrame) -> None:
    counts = df["group"].value_counts().reindex(GROUP_ORDER)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(counts.index, counts.values, color=[GROUP_COLORS[g] for g in counts.index])
    total = counts.sum()
    for b, v in zip(bars, counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}\n({v/total*100:.1f}%)",
                ha="center", va="bottom", fontsize=9)
    ax.set_title("청년삶 2024 노동상태 4집단 표본 수")
    ax.set_ylabel("응답자 수 (명)")
    ax.margins(y=0.15)
    _save(fig, "03_group_sizes.png")


def fig_group_vulnerability(df: pd.DataFrame) -> None:
    """집단별 취약 지표(비율) 비교."""
    metrics = {
        "has_debt": "부채 보유",
        "has_living_cost_debt": "생활비 부채",
        "has_interest": "이자 부담",
        "no_help_flag": "도움줄 곳 없음",
        "not_parent_cohabit": "부모 비동거",
        "isolation_flag": "고립 경향",
    }
    agg = df.groupby("group")[list(metrics)].mean().reindex(GROUP_ORDER) * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(metrics))
    width = 0.2
    for i, g in enumerate(GROUP_ORDER):
        ax.bar([xi + i * width for xi in x], agg.loc[g].values, width,
               label=g, color=GROUP_COLORS[g])
    ax.set_xticks([xi + 1.5 * width for xi in x])
    ax.set_xticklabels(list(metrics.values()), rotation=15)
    ax.set_ylabel("해당 비율 (%)")
    ax.set_title("노동상태 집단별 취약 지표 비율")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "04_group_vulnerability.png")


def fig_rested_economic(df: pd.DataFrame) -> None:
    """차별점① — 경제 부담만 좁혀서: 쉬었음은 취업/실업자보다 더 쪼들리지 않는다."""
    metrics = {"has_debt": "부채 보유", "has_living_cost_debt": "생활비 부채",
               "has_interest": "이자 부담"}
    groups = ["취업자", "실업자", "쉬었음"]
    agg = df.groupby("group")[list(metrics)].mean().reindex(groups) * 100
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    x = range(len(metrics))
    width = 0.26
    for i, g in enumerate(groups):
        bars = ax.bar([xi + i * width for xi in x], agg.loc[g].values, width,
                      label=g, color=GROUP_COLORS[g])
        for b, v in zip(bars, agg.loc[g].values):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(list(metrics.values()))
    ax.set_ylabel("해당 비율 (%)")
    ax.set_title("차별점① 경제 부담 — 쉬었음은 오히려 가장 낮음")
    ax.legend(title="노동상태")
    ax.grid(axis="y", alpha=0.3)
    ax.margins(y=0.15)
    _save(fig, "04b_rested_economic.png")


def fig_rested_survival(df: pd.DataFrame) -> None:
    """step4 — 쉬었음 청년은 '무엇으로' 버티는가: 가족 중심 사적 안전망.

    평균 경제부담이 낮은 이유(=다수가 가족 울타리로 버팀)를 보여주고,
    제도(공공·민간)는 미미함을 드러내 다음 단계(울타리 없는 소수)로 잇는다.
    """
    rested = df[df["group"] == "쉬었음"]
    n = len(rested)

    def pct(col: str) -> float:
        return float(pd.to_numeric(rested[col], errors="coerce").eq(1).mean() * 100)

    bars = {
        "부모와 동거": float((1 - pd.to_numeric(rested["not_parent_cohabit"], errors="coerce")).mean() * 100),
        "가족 도움 가능": pct("help_living_family"),
        "지인 도움 가능": pct("help_living_acq"),
        "공공기관": pct("help_living_public"),
        "민간기관": pct("help_living_private"),
    }
    colors = ["#4C78A8", "#4C78A8", "#72B7B2", "#9D9D9D", "#9D9D9D"]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    b = ax.bar(list(bars), list(bars.values()), color=colors)
    for rect, v in zip(b, bars.values()):
        ax.text(rect.get_x() + rect.get_width() / 2, v, f"{v:.1f}%",
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylabel("쉬었음 청년 중 해당 비율 (%)")
    ax.set_title(f"쉬었음 청년은 무엇으로 버티는가 — 가족 중심 사적 안전망 (n={n:,})")
    ax.margins(y=0.18)
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.99, -0.16, "※ 가족·부모가 압도적, 공공·민간 제도는 미미 → 가족 의존형 생활 유지",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#666")
    _save(fig, "04c_rested_survival.png")


def fig_group_psych(df: pd.DataFrame) -> None:
    """집단별 주관적 지표 평균(삶 만족도·행복·주관적 계층)."""
    items = [("life_satisfaction", "삶 만족도 (0-10)"),
             ("happiness", "행복감 (0-10)"),
             ("subjective_class", "주관적 계층 (1-5)")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (col, title) in zip(axes, items):
        m = df.groupby("group")[col].mean().reindex(GROUP_ORDER)
        ax.bar(m.index, m.values, color=[GROUP_COLORS[g] for g in m.index])
        for i, v in enumerate(m.values):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=20)
        ax.margins(y=0.15)
    fig.suptitle("노동상태 집단별 주관적 웰빙 평균", y=1.02)
    _save(fig, "05_group_psych.png")


def fig_help_network(df: pd.DataFrame) -> None:
    """생활비 부족 시 지원망: 쉬었음 vs 취업자."""
    cols = {"help_living_family": "가족", "help_living_acq": "지인",
            "help_living_public": "공공기관", "help_living_private": "민간기관",
            "help_living_none": "없음"}
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(cols))
    width = 0.38
    for i, g in enumerate(["취업자", "쉬었음"]):
        sub = df[df["group"] == g]
        vals = [pd.to_numeric(sub[c], errors="coerce").eq(1).mean() * 100 for c in cols]
        ax.bar([xi + i * width for xi in x], vals, width, label=g,
               color=GROUP_COLORS[g])
    ax.set_xticks([xi + width / 2 for xi in x])
    ax.set_xticklabels(list(cols.values()))
    ax.set_ylabel("응답 비율 (%)")
    ax.set_title("생활비 부족 시 도움 가능한 곳 (취업자 vs 쉬었음)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "06_help_network.png")


def fig_klips_supplement(klips: pd.DataFrame) -> dict:
    """KLIPS 26차(2023) 청년 보조검증: 취업 vs 미취업 비교(소표본 주의)."""
    df = klips.copy()
    df["g"] = pd.NA
    df.loc[df["is_employed_klips"] == 1, "g"] = "취업"
    df.loc[df["is_nonemployed_klips"] == 1, "g"] = "미취업"
    df = df[df["g"].notna()]
    order = ["취업", "미취업"]
    n_emp = int((df["g"] == "취업").sum())
    n_non = int((df["g"] == "미취업").sum())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))
    # 가구 부채 보유율
    debt = df.groupby("g")["has_debt_klips"].mean().reindex(order) * 100
    ax1.bar(order, debt.values, color=["#4C78A8", "#E45756"])
    for i, v in enumerate(debt.values):
        ax1.text(i, v, f"{v:.1f}%", ha="center", va="bottom")
    ax1.set_title("가구 부채 보유율 (%)")
    ax1.set_ylabel("%")
    ax1.margins(y=0.15)
    # 작년 연간 근로소득 중앙값(만원)
    inc = df.groupby("g")["labor_income_year"].median().reindex(order)
    ax2.bar(order, inc.values, color=["#4C78A8", "#E45756"])
    for i, v in enumerate(inc.values):
        ax2.text(i, v, f"{v:,.0f}", ha="center", va="bottom")
    ax2.set_title("작년(2022) 연간 근로소득 중앙값 (만원)\n※회고형: 미취업자도 작년 근로분 포함")
    ax2.set_ylabel("만원")
    ax2.margins(y=0.15)
    fig.suptitle(f"[보조검증] KLIPS 2023 청년 취업 vs 미취업 "
                 f"(취업 n={n_emp}, 미취업 n={n_non})", y=1.03)
    _save(fig, "09_klips_supplement.png")
    return {"n_emp": n_emp, "n_non": n_non, "df": df}


def fig_within_rested(rested: pd.DataFrame, split_col: str, labels: dict, name: str, title: str) -> None:
    """쉬었음 내부 2집단 비교(비율 지표 + 평균 지표)."""
    prop_metrics = {"has_debt": "부채 보유", "no_help_flag": "도움없음", "isolation_flag": "고립"}
    mean_metrics = {"life_satisfaction": "삶만족(0-10)", "vuln_score": "취약점수(0-6)",
                    "subjective_class": "주관계층(1-5)"}
    # 분할 기준 변수 자체(및 vuln_score가 그 구성요소면)는 동어반복이므로 제외
    prop_metrics = {k: v for k, v in prop_metrics.items() if k != split_col}
    if split_col in _VULN_COMPONENTS:
        mean_metrics = {k: v for k, v in mean_metrics.items() if k != "vuln_score"}
    groups = list(labels)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    x = range(len(prop_metrics))
    width = 0.38
    for i, g in enumerate(groups):
        sub = rested[rested[split_col] == g]
        vals = [pd.to_numeric(sub[c], errors="coerce").mean() * 100 for c in prop_metrics]
        ax1.bar([xi + i * width for xi in x], vals, width, label=labels[g])
    ax1.set_xticks([xi + width / 2 for xi in x])
    ax1.set_xticklabels(list(prop_metrics.values()))
    ax1.set_ylabel("비율 (%)")
    ax1.set_title("취약 지표 비율")
    ax1.legend()

    x = range(len(mean_metrics))
    for i, g in enumerate(groups):
        sub = rested[rested[split_col] == g]
        vals = [pd.to_numeric(sub[c], errors="coerce").mean() for c in mean_metrics]
        ax2.bar([xi + i * width for xi in x], vals, width, label=labels[g])
    ax2.set_xticks([xi + width / 2 for xi in x])
    ax2.set_xticklabels(list(mean_metrics.values()))
    ax2.set_ylabel("평균")
    ax2.set_title("주관/취약 평균")
    ax2.legend()

    fig.suptitle(title, y=1.02)
    _save(fig, name)


# ----------------------------------------------------------------------
# 통계 검정 출력
# ----------------------------------------------------------------------
# vuln_score 의 구성요소(이 변수로 집단을 나누면 vuln_score 비교는 동어반복)
_VULN_COMPONENTS = {"not_parent_cohabit", "no_help_flag", "family_help_flag",
                    "has_debt", "has_living_cost_debt", "has_interest"}


def _print_tests(df: pd.DataFrame) -> None:
    print("\n========== 통계 검정 (Mann-Whitney / 카이제곱 + 효과크기) ==========")

    def block(title, gcol, ga, gb, sub=None):
        data = sub if sub is not None else df
        print(f"\n[{title}]  (A={ga}, B={gb})")
        for v in ("life_satisfaction", "vuln_score", "subjective_class", "future_feasibility"):
            if v == gcol:
                continue
            if v == "vuln_score" and gcol in _VULN_COMPONENTS:
                continue  # 동어반복 방지
            r = q.mann_whitney_compare(data, gcol, v, ga, gb)
            if r["p"] is None:
                print(f"  - {v:18s}: {r['효과해석']}")
                continue
            print(f"  - {v:18s}: 중앙값 {r['중앙값_A']} vs {r['중앙값_B']} | "
                  f"p={r['p']:.3g} {r['유의']} | r={r['효과크기r']}({r['효과해석']})")
        for v in ("has_debt", "no_help_flag", "isolation_flag", "has_living_cost_debt"):
            if v == gcol:
                continue
            r = q.chi_square_compare(data, gcol, v, ga, gb)
            if r.get("p") is None:
                print(f"  - {v:18s}: {r['유의']}")
                continue
            warn = f" *{r.get('경고')}" if r.get("경고") else ""
            print(f"  - {v:18s}: 비율 {r['비율A(%)']}% vs {r['비율B(%)']}% | "
                  f"p={r['p']:.3g} {r['유의']} | V={r['효과크기V']}({r['효과해석']}){warn}")

    block("쉬었음 vs 실업자", "group", "쉬었음", "실업자")
    block("쉬었음 vs 취업자", "group", "쉬었음", "취업자")

    rested = df[df["group"] == "쉬었음"].copy()
    block("쉬었음 내부: 부모비동거 vs 동거", "not_parent_cohabit", 1, 0, sub=rested)
    block("쉬었음 내부: 도움없음 vs 도움있음", "no_help_flag", 1, 0, sub=rested)


def main() -> int:
    _setup_font()
    if not q.db_exists():
        print("[insights] DB가 없습니다. 먼저 preprocess + build_db 를 실행하세요.")
        return 1

    df = _add_group_en(q.run_query("SELECT * FROM youth_life_2024_analysis"))
    print(f"[insights] 청년삶 2024 분석표: {len(df):,} 행")

    print("[insights] EAPS 배경 추이 그림 생성...")
    try:
        eaps = q.run_query("SELECT * FROM eaps_labor_status_summary")
        fig_eaps_trends(eaps)
        fig_youth_unemp_vs_rested(eaps)
    except Exception as exc:  # noqa: BLE001
        print(f"  [건너뜀] EAPS 그림 실패: {exc}")

    print("[insights] 청년삶 집단 비교 그림 생성...")
    fig_group_overview(df)
    fig_group_vulnerability(df)
    fig_rested_economic(df)
    fig_rested_survival(df)
    fig_group_psych(df)
    fig_help_network(df)

    rested = df[df["group"] == "쉬었음"].copy()
    fig_within_rested(rested, "not_parent_cohabit",
                      {1: "부모 비동거", 0: "부모 동거"},
                      "07_rested_parent_compare.png",
                      "쉬었음 청년 내부 비교: 부모 동거 여부")
    fig_within_rested(rested, "no_help_flag",
                      {1: "도움 없음", 0: "도움 있음"},
                      "08_rested_help_compare.png",
                      "쉬었음 청년 내부 비교: 생활비 지원망 유무")

    _print_tests(df)

    print("\n[insights] KLIPS 보조검증 그림 생성...")
    try:
        klips = q.run_query("SELECT * FROM klips_youth_2023")
        info = fig_klips_supplement(klips)
        kd = info["df"]
        print(f"  KLIPS 청년 취업(n={info['n_emp']}) vs 미취업(n={info['n_non']}) — 소표본 해석 주의")
        r = q.chi_square_compare(kd, "g", "has_debt_klips", "미취업", "취업")
        if r.get("p") is not None:
            warn = f" *{r.get('경고')}" if r.get("경고") else ""
            print(f"  - 가구부채보유율: 미취업 {r['비율A(%)']}% vs 취업 {r['비율B(%)']}% | "
                  f"p={r['p']:.3g} {r['유의']} | V={r['효과크기V']}{warn}")
        r2 = q.mann_whitney_compare(kd, "g", "labor_income_year", "미취업", "취업")
        if r2["p"] is not None:
            print(f"  - 연간근로소득: 중앙값 미취업 {r2['중앙값_A']} vs 취업 {r2['중앙값_B']} 만원 | "
                  f"p={r2['p']:.3g} {r2['유의']} | r={r2['효과크기r']}({r2['효과해석']})")
    except Exception as exc:  # noqa: BLE001
        print(f"  [건너뜀] KLIPS 그림 실패: {exc}")

    print("\n[insights] 완료. 그림은 outputs/figures 에 저장되었습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
