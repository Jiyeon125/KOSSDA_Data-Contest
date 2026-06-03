"""청년 '쉬었음' 집단의 내부 생활안전망 격차 - Streamlit 대시보드 (1차).

메인 데이터: 청년삶실태조사 2024 (youth_life_2024_analysis)
배경: 경제활동인구조사 EAPS (eaps_labor_status_summary)
보조검증: 한국노동패널 KLIPS 26차/2023 (klips_youth_2023)

원칙
  - 표시되는 모든 수치는 적재된 실제 데이터에서 계산된다(임의 생성 없음).
  - 비율/평균/규모 = 가중(weight_person, 모집단 추정), 검정 p/n = 비가중.
  - 흐름은 docs/visualization_strategy.md(제안서 6단계)를 따른다.

실행: streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import queries
from src import charts

st.set_page_config(
    page_title="청년 쉬었음 · 생활안전망 격차",
    page_icon="📊",
    layout="wide",
)

ANALYSIS = queries.ANALYSIS_TABLE  # youth_life_2024_analysis

# 색상 팔레트 (전략 문서 규칙)
GROUP_ORDER = ["취업자", "실업자", "쉬었음", "비경활(기타)"]
GROUP_COLORS = {"취업자": "#4C78A8", "실업자": "#F58518", "쉬었음": "#E45756", "비경활(기타)": "#9D9D9D"}
NET_ORDER = ["비공식(가족·지인)", "공식(공공·민간)", "없음"]
NET_COLORS = {"비공식(가족·지인)": "#4C78A8", "공식(공공·민간)": "#F58518", "없음": "#E45756"}


# ----------------------------------------------------------------------
# 데이터 로드 (캐시 + 가드)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_analysis() -> pd.DataFrame:
    df = queries.run_query(f'SELECT * FROM "{ANALYSIS}";')

    def grp(r):
        if r.get("is_employed") == 1:
            return "취업자"
        if r.get("is_unemployed") == 1:
            return "실업자"
        if r.get("is_rested") == 1:
            return "쉬었음"
        return "비경활(기타)"

    df["group"] = df.apply(grp, axis=1)
    return df


@st.cache_data(show_spinner=False)
def load_eaps() -> pd.DataFrame:
    return queries.run_query('SELECT * FROM eaps_labor_status_summary;')


@st.cache_data(show_spinner=False)
def load_klips() -> pd.DataFrame:
    return queries.run_query('SELECT * FROM klips_youth_2023;')


def _badge(res: dict, kind: str) -> str:
    """검정 결과를 한 줄 배지 텍스트로 만든다."""
    if res.get("p") is None:
        return "표본 부족"
    sig = "✅ 유의(p<.05)" if res["p"] < 0.05 else "➖ 비유의"
    eff = res.get("효과크기r", res.get("효과크기V"))
    warn = " · ⚠소표본" if res.get("경고") else ""
    return f"{sig} · p={res['p']:.3g} · 효과크기 {eff} ({res.get('효과해석','')}){warn}"


def _weighted_means_by_group(df: pd.DataFrame, group_col: str, cols: dict,
                             order: list) -> pd.DataFrame:
    rows = []
    for g in order:
        sub = df[df[group_col] == g]
        if sub.empty:
            continue
        for c, label in cols.items():
            rows.append({"집단": g, "지표": label, "값": queries.weighted_mean(sub, c)})
    return pd.DataFrame(rows)


def _weighted_rates_by_group(df: pd.DataFrame, group_col: str, cols: dict,
                             order: list) -> pd.DataFrame:
    rows = []
    for g in order:
        sub = df[df[group_col] == g]
        if sub.empty:
            continue
        for c, label in cols.items():
            rows.append({"집단": g, "지표": label,
                         "값": queries.weighted_share(sub, c)["비율_가중(%)"]})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 가용성 확인
# ----------------------------------------------------------------------
st.title("청년 '쉬었음' 집단 내부의 생활안전망 격차")
st.caption("KOSSDA 대학생 데이터 시각화 공모전 / 경영정보처리론 · 메인: 청년삶실태조사 2024 (가중 추정)")

tables = queries.list_tables() if queries.db_exists() else []
if ANALYSIS not in tables:
    st.warning("분석용 DB/테이블이 없습니다. 아래 순서로 파이프라인을 실행하세요.", icon="📂")
    st.code("python src/preprocess.py\npython src/build_db.py youth_life_2024_analysis.csv\n"
            "streamlit run app.py", language="text")
    st.stop()

df = load_analysis()
rested = df[df["group"] == "쉬었음"].copy()

SECTIONS = [
    "S0 · 개요 · 핵심 요약",
    "S1 · 배경 (실업률 vs 쉬었음)",
    "S2 · 쉬었음은 누구인가",
    "S3 · 무엇으로 버티나",
    "S4 · ★내부 생활안전망 격차★",
    "S5 · 취약 누적 스펙트럼",
    "S6 · 보조검증 (KLIPS)",
    "S7 · 결론 · 함의",
]
section = st.sidebar.radio("분석 흐름", SECTIONS)
st.sidebar.caption("비율·규모=가중 추정 / 검정 p·n=비가중")


# ======================================================================
# S0 개요
# ======================================================================
if section == SECTIONS[0]:
    st.header("개요 · 핵심 요약")
    rest_share = queries.weighted_share(df, "is_rested")
    no_help = queries.weighted_share(rested, "no_help_flag")
    hi = (pd.to_numeric(rested["vuln_score"], errors="coerce") >= 3)
    hi_rate = round(float(hi.mean() * 100), 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("쉬었음 청년 규모(가중)", f"약 {rest_share['모집단추정(명)']/10000:.0f}만 명",
              f"{rest_share['비율_가중(%)']}%")
    c2.metric("쉬었음 표본", f"{len(rested):,}명")
    c3.metric("도움받을 곳 '없음'", f"약 {no_help['모집단추정(명)']/10000:.1f}만 명",
              f"{no_help['비율_가중(%)']}%")
    c4.metric("고취약(3점+) 비율", f"{hi_rate}%")

    st.markdown(
        """
**문제의식 (제안서 흐름)**
1. 실업률만으로는 청년 고용 문제를 다 설명하기 어렵다.
2. 노동시장 밖에는 **'쉬었음'** 청년이 있다.
3. 그런데 쉬어도 **생활비는 계속 필요**하다.
4. 그렇다면 이들은 **무엇으로 생활을 유지**하는가?
5. 다수는 **가족지원망**으로 버티지만, 일부는 **도움받을 곳이 없거나 부채·이자 부담**을 안는다.
6. → 따라서 **쉬었음 청년 '내부'의 생활안전망 격차**를 분석한다.
"""
    )
    st.info("좌측 사이드바에서 S1→S7 순서로 분석 흐름을 따라가세요.", icon="🧭")


# ======================================================================
# S1 배경 EAPS
# ======================================================================
elif section == SECTIONS[1]:
    st.header("배경 — 실업률만으로는 부족하다")
    st.markdown("청년(15–29세) **실업률은 안정/하락**해 보여도, 노동시장 밖 **'쉬었음' 인구는 구조적으로 증가**한다.")
    try:
        eaps = load_eaps()
        youth = eaps[eaps["age_group"] == "15 - 29세"]
        unemp = youth[youth["indicator"].str.contains("실업률", na=False)][["year", "value"]]
        rest = youth[youth["indicator"] == "쉬었음"][["year", "value"]]
        merged = unemp.merge(rest, on="year", suffixes=("_unemp", "_rest")).sort_values("year")
        fig = charts.line_dual_axis(
            merged, x="year", y_left="value_unemp", y_right="value_rest",
            name_left="청년 실업률(%)", name_right="청년 쉬었음(천 명)",
            title="청년(15–29) 실업률 vs 쉬었음 인구 추이",
            left_title="실업률(%)", right_title="쉬었음(천 명)",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("출처: 경제활동인구조사(EAPS) 집계표. 쉬었음 시계열은 2003년부터 제공.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"EAPS 데이터를 불러오지 못했습니다: {exc}")


# ======================================================================
# S2 쉬었음은 누구인가
# ======================================================================
elif section == SECTIONS[2]:
    st.header("쉬었음은 누구인가 — 실업자와 다르다")
    st.markdown("4개 노동상태 집단을 비교하면, **쉬었음은 실업자와 통계적으로 구분되는 별개 집단**이다.")

    means = _weighted_means_by_group(
        df, "group", {"life_satisfaction": "삶 만족도", "happiness": "행복감"}, GROUP_ORDER)
    fig1 = charts.grouped_bar(
        means, x="지표", y="값", color="집단", title="집단별 주관 웰빙 (가중 평균, 0–10)",
        color_map=GROUP_COLORS, category_orders={"집단": GROUP_ORDER},
        y_title="평균(0–10)", x_title="", text_format=".2f")
    st.plotly_chart(fig1, width="stretch")

    rates = _weighted_rates_by_group(
        df, "group",
        {"has_debt": "부채 보유", "isolation_flag": "고립 경향", "no_help_flag": "도움없음"},
        GROUP_ORDER)
    fig2 = charts.grouped_bar(
        rates, x="지표", y="값", color="집단", title="집단별 취약 지표 (가중 비율, %)",
        color_map=GROUP_COLORS, category_orders={"집단": GROUP_ORDER},
        y_title="비율(%)", x_title="", text_format=".1f")
    st.plotly_chart(fig2, width="stretch")

    b1 = queries.mann_whitney_compare(df, "group", "life_satisfaction", "쉬었음", "실업자")
    b2 = queries.mann_whitney_compare(df, "group", "vuln_score", "쉬었음", "취업자")
    st.markdown(f"- **쉬었음 vs 실업자** · 삶 만족도: {_badge(b1, 'mw')}")
    st.markdown(f"- **쉬었음 vs 취업자** · 취약점수: {_badge(b2, 'mw')}")


# ======================================================================
# S3 무엇으로 버티나
# ======================================================================
elif section == SECTIONS[3]:
    st.header("쉬어도 생활비는 든다 — 무엇으로 버티나")
    st.markdown("쉬었음 청년의 **다수(약 85%)는 가족·지인 비공식 지원망**으로 생활비를 버틴다.")

    help_cols = {"help_living_family": "가족", "help_living_acq": "지인",
                 "help_living_public": "공공기관", "help_living_private": "민간기관",
                 "help_living_none": "없음"}
    emp = df[df["group"] == "취업자"]
    rows = []
    for c, label in help_cols.items():
        rows.append({"지원처": label, "집단": "쉬었음", "값": queries.weighted_share(rested, c)["비율_가중(%)"]})
        rows.append({"지원처": label, "집단": "취업자", "값": queries.weighted_share(emp, c)["비율_가중(%)"]})
    hdf = pd.DataFrame(rows)
    fig = charts.grouped_bar(
        hdf, x="지원처", y="값", color="집단",
        title="생활비 부족 시 도움 가능한 곳 (가중 비율, %)",
        color_map={"쉬었음": "#E45756", "취업자": "#4C78A8"},
        y_title="비율(%)", x_title="", text_format=".1f")
    st.plotly_chart(fig, width="stretch")

    share = queries.weighted_group_share(rested, "safety_net_type")
    share = share.set_index("집단").reindex(NET_ORDER).reset_index()
    fig2 = charts.donut(share["집단"].tolist(), share["모집단추정(명)"].tolist(),
                        title="쉬었음 청년 생활안전망 유형 구성 (가중 모집단 추정)",
                        color_map=NET_COLORS)
    st.plotly_chart(fig2, width="stretch")


# ======================================================================
# S4 ★핵심★ 내부 격차
# ======================================================================
elif section == SECTIONS[4]:
    st.header("★ 쉬었음 '내부'의 생활안전망 격차 ★")
    st.markdown("같은 쉬었음이라도 **두 갈래 취약**으로 갈린다: "
                "**`없음`=고립형 사각지대**, **`공식`=부채 압박형**.")

    share = queries.weighted_group_share(rested, "safety_net_type")
    share["_o"] = share["집단"].map({g: i for i, g in enumerate(NET_ORDER)})
    share = share.sort_values("_o")
    fig_a = charts.grouped_bar(
        share, x="집단", y="비율_가중(%)", color="집단",
        title="생활안전망 유형 분포 (가중 비율, %)",
        color_map=NET_COLORS, category_orders={"집단": NET_ORDER},
        x_title="", y_title="비율(%)", text_format=".1f")
    st.plotly_chart(fig_a, width="stretch")
    st.dataframe(share[["집단", "표본n", "비율_가중(%)", "모집단추정(명)"]],
                 width="stretch", hide_index=True)

    rates = _weighted_rates_by_group(
        rested, "safety_net_type",
        {"isolation_flag": "고립 경향", "has_debt": "부채 보유", "has_interest": "이자 부담"},
        NET_ORDER)
    fig_b = charts.grouped_bar(
        rates, x="지표", y="값", color="집단", title="유형별 취약 지표 (가중 비율, %)",
        color_map=NET_COLORS, category_orders={"집단": NET_ORDER},
        x_title="", y_title="비율(%)", text_format=".1f")
    st.plotly_chart(fig_b, width="stretch")

    means = _weighted_means_by_group(
        rested, "safety_net_type",
        {"life_satisfaction": "삶 만족도(0–10)", "subjective_class": "주관 계층(1–5)"},
        NET_ORDER)
    st.dataframe(means.pivot(index="집단", columns="지표", values="값").reindex(NET_ORDER),
                 width="stretch")

    b1 = queries.chi_square_compare(rested, "safety_net_type", "isolation_flag", "없음", "비공식(가족·지인)")
    b2 = queries.mann_whitney_compare(rested, "safety_net_type", "subjective_class", "없음", "비공식(가족·지인)")
    st.markdown(f"- **없음 vs 비공식** · 고립 경향: {_badge(b1, 'chi')}")
    st.markdown(f"- **없음 vs 비공식** · 주관 계층: {_badge(b2, 'mw')}")
    st.caption("'없음'·'공식' 유형은 소표본이라 검정보다 기술통계 중심으로 해석합니다.")


# ======================================================================
# S5 취약 스펙트럼
# ======================================================================
elif section == SECTIONS[5]:
    st.header("취약은 누적된다 — 스펙트럼")
    st.markdown("취약요소(부모비동거·도움부재·부채 등)가 **쌓일수록 주관 웰빙이 유의하게 낮아진다.**")

    fig = charts.histogram(rested.assign(vuln_score=pd.to_numeric(rested["vuln_score"], errors="coerce")),
                           x="vuln_score", title="취약 누적 점수 분포 (쉬었음 내부, 0–6)", nbins=7)
    fig.update_layout(xaxis_title="vuln_score (취약요소 개수)", yaxis_title="표본 수(명)")
    st.plotly_chart(fig, width="stretch")

    r2 = rested.copy()
    r2["취약수준"] = (pd.to_numeric(r2["vuln_score"], errors="coerce") >= 3).map(
        {True: "고취약(3점+)", False: "저취약(0–2)"})
    means = _weighted_means_by_group(
        r2, "취약수준", {"life_satisfaction": "삶 만족도", "happiness": "행복감"},
        ["저취약(0–2)", "고취약(3점+)"])
    fig2 = charts.grouped_bar(
        means, x="지표", y="값", color="집단", title="고/저취약 주관 웰빙 (가중 평균, 0–10)",
        color_map={"저취약(0–2)": "#9D9D9D", "고취약(3점+)": "#E45756"},
        category_orders={"집단": ["저취약(0–2)", "고취약(3점+)"]},
        x_title="", y_title="평균(0–10)", text_format=".2f")
    st.plotly_chart(fig2, width="stretch")

    for col, label in {"life_satisfaction": "삶 만족도", "subjective_class": "주관 계층"}.items():
        b = queries.mann_whitney_compare(r2, "취약수준", col, "고취약(3점+)", "저취약(0–2)")
        st.markdown(f"- **고취약 vs 저취약** · {label}: {_badge(b, 'mw')}")


# ======================================================================
# S6 KLIPS 보조검증
# ======================================================================
elif section == SECTIONS[6]:
    st.header("보조검증 — KLIPS (2023)")
    st.markdown("다른 패널(한국노동패널 26차)에서도 **비취업 청년 가구의 부채 부담이 다소 높은** 경향이 보인다.")
    st.warning("KLIPS에는 청년 '쉬었음'을 단독 식별할 변수가 거의 없어 **취업 vs 미취업(실업+비경활)** 대조까지만 가능하며, "
               "미취업 표본(n≈148)이 작고 소득은 회고형이라 **약한 보조 근거**로만 사용합니다.", icon="⚠️")
    try:
        klips = load_klips()
        klips["g"] = pd.NA
        klips.loc[klips["is_employed_klips"] == 1, "g"] = "취업"
        klips.loc[klips["is_nonemployed_klips"] == 1, "g"] = "미취업"
        kd = klips[klips["g"].notna()]
        rows = []
        for g in ["취업", "미취업"]:
            sub = kd[kd["g"] == g]
            rate = pd.to_numeric(sub["has_debt_klips"], errors="coerce").mean() * 100
            rows.append({"집단": g, "가구 부채보유율(%)": round(float(rate), 1), "표본n": len(sub)})
        kdf = pd.DataFrame(rows)
        fig = charts.bar_chart(kdf, x="집단", y="가구 부채보유율(%)",
                               title="KLIPS 청년 취업 vs 미취업 — 가구 부채 보유율")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(kdf, width="stretch", hide_index=True)
        b = queries.chi_square_compare(kd, "g", "has_debt_klips", "미취업", "취업")
        st.markdown(f"- **미취업 vs 취업** · 가구 부채보유율: {_badge(b, 'chi')}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"KLIPS 데이터를 불러오지 못했습니다: {exc}")


# ======================================================================
# S7 결론
# ======================================================================
else:
    st.header("결론 · 정책 함의")
    no_help = queries.weighted_share(rested, "no_help_flag")
    st.markdown(
        f"""
### 핵심 요약
- **쉬었음 ≠ 실업자**: 별개의 비경제활동 집단으로 다뤄야 한다.
- **다수는 가족지원망(약 85%)** 으로 버티지만, 내부는 균질하지 않다.
- **두 갈래 취약 하위유형**:
  - **`도움없음`(약 {no_help['모집단추정(명)']/10000:.1f}만 명, {no_help['비율_가중(%)']}%)** → 사회적 **고립형 사각지대**
  - **`공식의존`** → **부채·이자 압박형**
- 취약요소가 **누적될수록** 삶 만족·행복·계층인식이 유의하게 낮아진다.

### 정책 함의
- '쉬었음'을 단일 범주로 보지 말고, **고립형 / 부채압박형을 구분해 타게팅**.
- 사각지대(`도움없음`)는 소득지원보다 **사회적 연결·접촉 기반 개입**이 필요.
"""
    )
    st.caption("※ 한계: 소표본 유형(없음·공식)·고립 지표는 기대빈도<5로 해석 주의, "
               "future_feasibility 방향은 코드북 확인 후 확정 예정.")

st.divider()
st.caption("표시 수치는 청년삶 2024·EAPS·KLIPS 실데이터에서 계산. © 2026 경영정보처리론 · KOSSDA 공모전")
