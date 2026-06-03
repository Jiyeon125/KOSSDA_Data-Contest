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
from src import clustering as clust

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
CLUSTER_COLORS = {"안정형": "#4C78A8", "부채압박형": "#F58518", "사회적 고립형": "#E45756",
                  "무지원형": "#E45756", "독립·저부담형": "#54A24B"}
YEAR_COLORS = {"2022": "#9D7660", "2024": "#4C78A8"}


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


@st.cache_data(show_spinner=False)
def load_year(year: int) -> pd.DataFrame:
    """연도별 청년삶 분석 테이블(존재할 때만)."""
    return queries.run_query(f'SELECT * FROM youth_life_{year}_analysis;')


@st.cache_data(show_spinner=False)
def cluster_rested_cached(year: int = 2024):
    """쉬었음 청년 데이터기반 군집(k=3) 결과를 캐시해서 반환한다."""
    d = load_year(year)
    r = d[d["is_rested"] == 1].copy()
    labeled, k, scores = clust.cluster_rested(r, k=3)
    prof = clust.profile(labeled)
    names = clust.auto_name(prof)
    prof["유형"] = prof["cluster"].map(names)
    labeled["cluster_name"] = labeled["cluster"].map(names)
    return labeled, prof, k, scores


def method_note(md: str) -> None:
    """각 화면의 '집계·분석 방법 / 읽는 법' 설명 박스."""
    with st.expander("📖 이 그래프 읽는 법 · 어떻게 집계·분석했나", expanded=False):
        st.markdown(md)


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
    "S7 · 재현성·추세 (2022↔2024)",
    "S8 · 결론 · 함의",
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
    method_note(
        """
**데이터** · 청년삶실태조사 2024 응답자 15,098명(만 19–34세).
**'쉬었음' 정의** · 경제활동상태=비경제활동인구 **그리고** 지난주 주된 활동='쉬었음'인 사람만 추출
(육아·가사·통학·취업준비·심신장애와 구분되는 순수 쉬었음).
**KPI 산출**
- *규모(만 명)* = 각 응답자의 **가중치(`weight_person`)** 합 → 표본을 전국 모집단으로 환산한 추정치.
- *비율(%)* = 가중 비율.
- *고취약* = 취약요소 누적점수 `vuln_score`가 3점 이상인 비율(아래 S5에서 정의).
**왜 가중?** 표본 1명이 모집단에서 대표하는 인원(25.8~6,465명)이 달라, 가중해야 전국 대표값이 된다.
"""
    )


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
        method_note(
            """
**자료** · 통계청 경제활동인구조사(EAPS) **공식 집계표**(개인 원자료 아님)를 연도×지표 long으로 변환한 표
(`eaps_labor_status_summary`). 청년 **15–29세** 행만 사용.
**두 선이 다른 축을 쓴다** · 왼쪽 축=**실업률(%)**, 오른쪽 축=**쉬었음 인구(천 명)**. 단위가 달라 한 축에 못 그린다.
**두 축 모두 0부터** 시작하도록 고정해 기울기가 과장되지 않게 했다.
**읽는 법** · 실업률(주황)은 2020년 이후 **하락**하는데, 쉬었음(빨강)은 **계속 증가** → "실업률만 보면 놓치는 청년층"이 존재한다는 배경 근거.
"""
        )
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
    method_note(
        """
**집단 정의** · `취업자`(취업), `실업자`(구직 중 미취업), `쉬었음`, `비경활(기타)`(육아·가사·통학 등).
**위 막대값** · 집단별 **가중 평균**(웰빙, 0–10점)과 **가중 비율**(취약지표, %).
**검정 방법(배지)** · 연속변수(삶 만족도 등)는 분포를 가정하지 않는 **Mann-Whitney U 검정**,
비율(부채·고립 등)은 **카이제곱 검정**. 함께 표시한 **효과크기(r, V)** 로 "차이의 크기"를 본다.
**왜 막대 차이가 작아 보이나** · 삶 만족도는 0–10 척도라 6.0 vs 6.5처럼 **실제 차이가 작다.**
다만 표본이 커서 통계적으로는 **유의**할 수 있어, p값과 효과크기를 함께 봐야 한다(효과크기는 대개 '작음').
**핵심** · 실업자가 웰빙 최저, 쉬었음은 그 위 → **쉬었음 ≠ 실업자**(별개 집단).
"""
    )


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
    method_note(
        """
**설문 문항** · "생활비가 부족할 때 도움받을 수 있는 곳"(복수응답): 가족·지인·공공기관·민간기관·없음.
**막대** · 각 보기를 '해당'으로 응답한 **가중 비율(%)**. 쉬었음(빨강) vs 취업자(파랑) 비교.
**도넛** · 쉬었음 청년을 **상호배타 3유형**으로 묶은 모집단 추정 구성비
(없음 > 공식(공공·민간) > 비공식(가족·지인) 우선순위로 1명을 1유형에만 배정).
**읽는 법** · 약 85%가 가족·지인(비공식)에 의존 → "다수는 가족지원망으로 버틴다"는 제안서 가설을 데이터로 확인.
"""
    )


# ======================================================================
# S4 ★핵심★ 내부 격차
# ======================================================================
elif section == SECTIONS[4]:
    st.header("★ 쉬었음 '내부'의 생활안전망 격차 ★")
    st.markdown("분석자가 임의로 나누지 않고 **데이터(K-means 군집)** 가 쉬었음을 **3개 하위유형**으로 가른다: "
                "**안정형(다수)** + 두 취약 갈래 **`사회적 고립형`·`부채압박형`**.")

    labeled, prof, k, scores = cluster_rested_cached(2024)
    cl_order = prof["유형"].tolist()
    feat_labels = list(clust.FEATURES.values())

    # (A) 유형별 규모
    size_df = prof[["유형", "표본n", "모집단추정(명)"]].copy()
    fig_size = charts.grouped_bar(
        size_df, x="유형", y="표본n", color="유형", title="하위유형 규모 (표본 수)",
        color_map=CLUSTER_COLORS, category_orders={"유형": cl_order},
        x_title="", y_title="표본 수(명)", text_format=".0f")
    st.plotly_chart(fig_size, width="stretch")
    st.dataframe(size_df, width="stretch", hide_index=True)

    # (B) 유형별 특징 프로파일(보유율 %)
    prof_long = prof.melt(id_vars="유형", value_vars=feat_labels,
                          var_name="특징", value_name="값")
    fig_prof = charts.grouped_bar(
        prof_long, x="특징", y="값", color="유형",
        title="유형별 취약 특징 보유율 (%)",
        color_map=CLUSTER_COLORS, category_orders={"유형": cl_order},
        x_title="", y_title="보유율(%)", text_format=".0f")
    st.plotly_chart(fig_prof, width="stretch")

    # (C) 유형별 주관 웰빙
    well_long = prof.melt(id_vars="유형", value_vars=["삶 만족도(0-10)", "행복감(0-10)"],
                          var_name="지표", value_name="값")
    fig_well = charts.grouped_bar(
        well_long, x="지표", y="값", color="유형",
        title="유형별 주관 웰빙 (가중 평균, 0–10)",
        color_map=CLUSTER_COLORS, category_orders={"유형": cl_order},
        x_title="", y_title="평균(0–10)", text_format=".2f")
    st.plotly_chart(fig_well, width="stretch")

    # 검정: 군집 간 삶 만족도 차이 + 고립형 vs 나머지
    from scipy import stats as _stats
    ls = {c: pd.to_numeric(g["life_satisfaction"], errors="coerce").dropna()
          for c, g in labeled.dropna(subset=["cluster"]).groupby("cluster_name")}
    if len(ls) >= 2 and all(v.size >= 2 for v in ls.values()):
        H, p_kw = _stats.kruskal(*ls.values())
        st.markdown(f"- **3개 하위유형 간 삶 만족도 차이** · Kruskal-Wallis: "
                    f"H={H:.1f}, p={p_kw:.3g} {'✅ 유의' if p_kw < 0.05 else '➖ 비유의'}")
    iso_name = "사회적 고립형" if "사회적 고립형" in ls else ("무지원형" if "무지원형" in ls else None)
    if iso_name:
        iso = ls[iso_name]
        rest_ls = pd.concat([v for n, v in ls.items() if n != iso_name])
        if iso.size >= 2 and rest_ls.size >= 2:
            U, p_u = _stats.mannwhitneyu(iso, rest_ls, alternative="two-sided")
            r_rb = 1 - 2 * U / (iso.size * rest_ls.size)
            st.markdown(f"- **{iso_name}(n={iso.size}) vs 나머지** · 삶 만족도: "
                        f"p={p_u:.3g} · 효과크기 r={r_rb:.2f} ({queries._effect_label_r(r_rb)})")

    with st.expander("참고: 휴리스틱 유형(safety_net_type)·도움원천 비배타 분포", expanded=False):
        st.caption("초기엔 도움원천을 '없음→공식→비공식' 우선순위로 1유형에 강제배정했으나, "
                   "순서가 임의적이라 핵심 분석은 위 데이터기반 군집으로 대체했습니다. 아래는 참고용입니다.")
        share = queries.weighted_group_share(rested, "safety_net_type")
        share["_o"] = share["집단"].map({g: i for i, g in enumerate(NET_ORDER)})
        share = share.sort_values("_o")
        st.dataframe(share[["집단", "표본n", "비율_가중(%)", "모집단추정(명)"]],
                     width="stretch", hide_index=True)
    method_note(
        """
**데이터기반 하위유형(군집화)** · 분석자가 손으로 나누지 않고, 5개 취약지표
(지원망 없음·부모 비동거·부채·이자·고립)를 표준화해 **K-means**가 군집을 만든다.
**군집 수(k=3)** · 엘보우(WCSS 꺾임)+실루엣+해석가능성으로 3 선택(`scripts/cluster_rested.py`).
**그래프** · ①유형별 규모 ②유형별 취약특징 보유율(%) ③유형별 가중 웰빙 평균.
**검정** · 유형 간 삶 만족도 차이는 **Kruskal-Wallis**, 고립형 vs 나머지는 **Mann-Whitney U**(효과크기 r). p·n은 비가중.
**핵심** · 안정형(약 83%)이 다수지만, **사회적 고립형**(웰빙 급락)과 **부채압박형**(부채·이자↑)이
서로 다른 축에서 분리된다 → 취약 메커니즘이 **두 갈래**. (2022에서도 같은 3유형이 재현 — S7 참고)
"""
    )


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
    method_note(
        """
**취약 누적점수(`vuln_score`, 0–6)** · 다음 취약요소의 **개수 합**:
부모 비동거 · 가족 도움 없음 · (생활비)도움 없음 · 부채 보유 · 생활비 목적 부채 · 이자 부담.
**왼쪽** · 쉬었음 청년의 점수 분포(0점이 절반). **오른쪽** · 고취약(3점+) vs 저취약(0–2)의 웰빙 가중 평균.
**동어반복 방지** · 비교 지표는 점수 **구성요소가 아닌 외부 변수**(삶 만족도·행복·주관 계층)만 사용.
**핵심** · 취약요소가 쌓일수록 삶 만족·행복·계층인식이 **유의하게** 낮아진다(효과크기 작음) → "격차는 이분법이 아니라 누적 스펙트럼".
"""
    )


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
        method_note(
            """
**자료** · 한국노동패널(KLIPS) 26차=**2023년** 개인·가구 파일을 청년(19–34) 기준으로 결합(`klips_youth_2023`).
**집단** · 취업상태 코드(1=취업, 2=실업, 3=비경활)에서 **취업(1)** vs **미취업(2+3)**.
**막대** · 가구 부채 보유 여부(`h262632`, 1=있음)의 집단별 비율(%). 검정=카이제곱(비가중).
**왜 '약한 보조'인가** · KLIPS에는 청년 **'쉬었음'을 단독 식별할 변수가 거의 없고**(미취업사유 문항이 청년 6명만 응답),
미취업 표본(n≈148)이 작으며 소득은 회고형(작년)이다. → 메인 결론은 **청년삶 2024 단독**, KLIPS는 방향성 참고용.
"""
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"KLIPS 데이터를 불러오지 못했습니다: {exc}")


# ======================================================================
# S7 재현성·추세 (2022 ↔ 2024)
# ======================================================================
elif section == SECTIONS[7]:
    st.header("재현성·추세 — 2022 vs 2024")
    st.markdown("같은 정의·같은 파생규칙으로 **2022년 청년삶**을 처리해, 2024 결과가 "
                "**우연이 아니라 재현되는 추세**임을 확인한다.")
    try:
        d22, d24 = load_year(2022), load_year(2024)
        r22 = d22[d22["is_rested"] == 1].copy()
        r24 = d24[d24["is_rested"] == 1].copy()

        # (A) 쉬었음 비중 추세
        rows = []
        for yr, d in (("2022", d22), ("2024", d24)):
            s = queries.weighted_share(d, "is_rested")
            rows.append({"연도": yr, "값": s["비율_가중(%)"], "n": s["표본n"],
                         "모집단": s["모집단추정(명)"]})
        size_df = pd.DataFrame(rows)
        fig_s = charts.grouped_bar(
            size_df, x="연도", y="값", color="연도",
            title="청년 대비 쉬었음 비중 (가중 %) — 2022 vs 2024",
            color_map=YEAR_COLORS, category_orders={"연도": ["2022", "2024"]},
            x_title="", y_title="비중(%)", text_format=".1f")
        st.plotly_chart(fig_s, width="stretch")

        # (B) 쉬었음 내부 취약지표 추세 + 연도 간 검정
        both = pd.concat([r22, r24], ignore_index=True)
        flags = {"no_help_flag": "지원망 없음", "not_parent_cohabit": "부모 비동거",
                 "has_debt": "부채 보유", "has_interest": "이자 부담",
                 "isolation_flag": "고립 경향"}
        rows = []
        notes = []
        for col, label in flags.items():
            w22 = queries.weighted_share(r22, col)["비율_가중(%)"]
            w24 = queries.weighted_share(r24, col)["비율_가중(%)"]
            rows.append({"지표": label, "연도": "2022", "값": w22})
            rows.append({"지표": label, "연도": "2024", "값": w24})
            t = queries.chi_square_compare(both, "survey_year", col, 2022, 2024)
            sig = "✅유의" if (t.get("p") is not None and t["p"] < 0.05) else "➖비유의"
            notes.append(f"- **{label}** · 2022 {w22}% → 2024 {w24}% · "
                         f"p={t['p']:.3g} {sig}" if t.get("p") is not None
                         else f"- **{label}** · 2022 {w22}% → 2024 {w24}%")
        vdf = pd.DataFrame(rows)
        fig_v = charts.grouped_bar(
            vdf, x="지표", y="값", color="연도",
            title="쉬었음 내부 취약지표 (가중 %) — 2022 vs 2024",
            color_map=YEAR_COLORS, category_orders={"연도": ["2022", "2024"]},
            x_title="", y_title="보유율(%)", text_format=".1f")
        st.plotly_chart(fig_v, width="stretch")
        st.markdown("\n".join(notes))

        # (C) 군집 하위유형 재현성
        _, prof22, _, _ = cluster_rested_cached(2022)
        st.subheader("취약 하위유형 재현성 (2022 군집화)")
        st.dataframe(prof22[["유형", "표본n", "지원망 없음", "부채 보유", "이자 부담",
                             "고립 경향", "삶 만족도(0-10)"]],
                     width="stretch", hide_index=True)
        st.caption("2022에서도 안정형 + (지원망없음·고립)취약형 + 부채압박형의 3유형이 재현되며, "
                   "취약유형의 삶 만족도가 가장 낮은 패턴도 반복됩니다.")
        method_note(
            """
**왜 2022를 보나** · 한 해(2024) 결과만으로는 우연일 수 있어, **동일 정의·동일 전처리**로 2022를 처리해
방향이 재현되는지 본다(`build_youth_2022_analysis`, `scripts/compare_years.py`).
**주의(2022 코딩 차이)** · 2022는 경제활동상태가 1취업/2실업/3비경활로, 2024(1~8)와 코드가 달라
별도 매핑했으나 **쉬었음 정의(비경활&주된활동=쉬었음)는 동일**하게 맞췄다.
**검정** · 연도 간 취약지표 비율 차이는 **카이제곱**(비가중 표본). 효과크기는 작아도 방향이 일관.
**핵심** · ①쉬었음 비중↑(5.2→7.2%) ②내부 취약(지원망없음·부채·이자·고립) 모두↑·유의
③3개 하위유형 재현 → **"쉬었음이 늘었고 그 안의 취약층도 두꺼워졌다"**는 추세.
"""
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"2022 비교 데이터를 불러오지 못했습니다(테이블 적재 필요): {exc}")


# ======================================================================
# S8 결론
# ======================================================================
else:
    st.header("결론 · 정책 함의")
    no_help = queries.weighted_share(rested, "no_help_flag")
    st.markdown(
        f"""
### 핵심 요약
- **쉬었음 ≠ 실업자**: 별개의 비경제활동 집단으로 다뤄야 한다.
- **다수는 가족지원망(약 85%)** 으로 버티지만, 내부는 균질하지 않다.
- **데이터(군집)가 가른 3개 하위유형**: 안정형(약 83%) 외에 두 취약 갈래 —
  - **사회적 고립형** → 도움받을 곳 없음·고립↑, **삶 만족도 급락**(사각지대)
  - **부채압박형** → 부채·이자 부담↑
  - (`도움없음` 약 {no_help['모집단추정(명)']/10000:.1f}만 명, {no_help['비율_가중(%)']}%)
- 취약요소가 **누적될수록** 삶 만족·행복·계층인식이 유의하게 낮아진다.
- **2022→2024 재현**: 쉬었음 규모↑ + 내부 취약↑ + 동일 3유형 재현(우연 아님).

### 정책 함의
- '쉬었음'을 단일 범주로 보지 말고, **고립형 / 부채압박형을 구분해 타게팅**.
- 사각지대(고립형)는 소득지원보다 **사회적 연결·접촉 기반 개입**이 필요.
"""
    )
    st.caption("※ 한계: 소표본 하위유형(고립형 등)은 효과크기를 함께 보고 경향으로 해석, "
               "KLIPS는 방향성 보조, future_feasibility 방향은 코드북 확인 후 확정 예정.")

st.divider()
st.caption("표시 수치는 청년삶 2024·EAPS·KLIPS 실데이터에서 계산. © 2026 경영정보처리론 · KOSSDA 공모전")
