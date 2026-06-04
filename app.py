"""청년 '쉬었음' 집단의 내부 취약 — 핵심 축 '사회적 고립' · Streamlit 대시보드.

확정 서사(LOCKED, docs/analysis_flow.md):
  배경(쉬었음↑) → 다수는 가족으로 버팀 → 내부 취약을 가르는 축은 돈이 아니라 '고립'
  → 공식 은둔지표·외부조사로 보강 → KGSS 전국에서도 '취업 아니라 고립'이 웰빙을 가름(재현)
  → 2022→2024 악화·재현 → 정책.

데이터: 청년삶실태조사 2024·2022(메인) / EAPS(배경) / KGSS(KOSSDA 기둥) / KLIPS(KOSSDA 보조)
원칙: 표시 수치는 적재된 실데이터에서 계산(임의 생성 없음). 비율·규모=가중, 검정 p·n=비가중.
       정밀 분석 그림(고립·은둔·KGSS·재현성)은 스크립트 산출 PNG를 그대로 게시(재현 가능).

실행: streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from scipy import stats

from src import queries
from src import charts

st.set_page_config(
    page_title="청년 쉬었음 · 고립의 사각지대",
    page_icon="📊",
    layout="wide",
)

ANALYSIS = queries.ANALYSIS_TABLE  # youth_life_2024_analysis
FIG_DIR = Path(__file__).resolve().parent / "outputs" / "figures"

# 색상 팔레트 (전략 문서 규칙)
GROUP_ORDER = ["취업자", "실업자", "쉬었음", "비경활(기타)"]
GROUP_COLORS = {"취업자": "#4C78A8", "실업자": "#F58518", "쉬었음": "#E45756", "비경활(기타)": "#9D9D9D"}
NET_ORDER = ["비공식(가족·지인)", "공식(공공·민간)", "없음"]
NET_COLORS = {"비공식(가족·지인)": "#4C78A8", "공식(공공·민간)": "#F58518", "없음": "#E45756"}
ISO_COLORS = {"비고립": "#9D9D9D", "고립": "#E45756"}
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
def load_year(year: int) -> pd.DataFrame:
    return queries.run_query(f'SELECT * FROM youth_life_{year}_analysis;')


@st.cache_data(show_spinner=False)
def load_kgss_summary() -> dict | None:
    """KGSS 분석 산출 요약(`scripts/kgss_isolation.py`)을 읽어 반환한다(없으면 None)."""
    p = Path(__file__).resolve().parent / "data" / "processed" / "kgss_isolation_summary.csv"
    if not p.exists():
        return None
    return pd.read_csv(p).iloc[0].to_dict()


# ----------------------------------------------------------------------
# 표시 헬퍼
# ----------------------------------------------------------------------
def show_fig(name: str, caption: str | None = None) -> None:
    """스크립트가 만든 분석 그림(PNG)을 게시한다(없으면 안내)."""
    p = FIG_DIR / name
    if p.exists():
        st.image(str(p), width="stretch", caption=caption)
    else:
        st.info(f"그림 `{name}` 이 아직 없습니다. 관련 스크립트를 실행해 생성하세요.", icon="🖼️")


def method_note(md: str) -> None:
    with st.expander("📖 이 화면 읽는 법 · 어떻게 집계·분석했나", expanded=False):
        st.markdown(md)


def _badge(res: dict) -> str:
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
st.title("'쉬었음' 청년의 진짜 위기는 어디에 있는가 — 돈이 아니라 '관계'")
st.caption("KOSSDA 대학생 데이터 시각화 공모전 / 경영정보처리론 · 메인: 청년삶실태조사 2024(가중 추정) · "
           "KOSSDA 소장: KGSS·KLIPS")

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
    "S3 · 무엇으로 버티나 (가족)",
    "S4 · ★취약의 핵심 축 = 고립★",
    "S5 · 고립의 심도 (공식 은둔)",
    "S6 · ★전국 일반화 (KGSS)★",
    "S7 · 재현성·추세 (2022↔2024)",
    "S8 · 결론 · 함의",
]
section = st.sidebar.radio("분석 흐름", SECTIONS)
st.sidebar.caption("비율·규모=가중 추정 / 검정 p·n=비가중")
st.sidebar.markdown("---")
st.sidebar.caption("📄 서사 단일출처: `docs/analysis_flow.md`\n\n🟢 PPT 초안: `발표_초안.md`")


# ======================================================================
# S0 개요
# ======================================================================
if section == SECTIONS[0]:
    st.header("개요 · 핵심 요약")
    rest_share = queries.weighted_share(df, "is_rested")
    no_help = queries.weighted_share(rested, "no_help_flag")
    iso = queries.weighted_share(rested, "isolation_flag")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("쉬었음 청년 규모(가중)", f"약 {rest_share['모집단추정(명)']/10000:.0f}만 명",
              f"{rest_share['비율_가중(%)']}%")
    c2.metric("쉬었음 표본", f"{len(rested):,}명")
    c3.metric("고립 경향", f"{iso['비율_가중(%)']}%", "삶만족 급락 축")
    c4.metric("도움받을 곳 '없음'", f"{no_help['비율_가중(%)']}%",
              f"약 {no_help['모집단추정(명)']/10000:.1f}만 명")

    st.markdown(
        """
**한 줄 메시지** · "'쉬었음' 청년 안에서 더 취약한 곳은 어디인가? → **고립된 청년**.
이는 전국 데이터(KGSS)에서도 **취업 여부보다 고립이 웰빙을 가른다**로 재현된다."

**서사 흐름(좌측 S1→S8)**
1. **배경** — 실업률은 안정·하락하는데 노동시장 밖 **'쉬었음'은 증가**(사각지대).
2. **정체성** — 쉬었음 ≠ 실업자(별개 비경활 집단).
3. **생존방식** — 다수(약 85%)는 **가족**으로 버틴다 → 평균이 내부 격차를 가린다.
4. ★ **취약의 핵심 축 = 사회적 고립** — 돈(부채)보다 **관계 단절**이 웰빙을 가른다.
5. **고립의 심도** — 공식 '은둔 기간'은 길수록 삶만족 단조 하락 + 외부 공식조사와 수렴.
6. ★ **전국 일반화(KGSS)** — 취업이 아니라 **고립**이 행복을 가른다(약 14배).
7. **재현·악화** — 2022→2024 쉬었음↑·내부 취약↑·가족 버팀목↓.
8. **결론** — 일자리를 넘어 **고립 해소·관계망 재건** 정책.
"""
    )
    st.info("좌측 사이드바에서 S1→S8 순서로 흐름을 따라가세요.", icon="🧭")
    method_note(
        """
**데이터** · 청년삶실태조사 2024 응답자 15,098명(만 19–34세).
**'쉬었음' 정의** · 경제활동상태=비경제활동 **그리고** 지난주 주된활동='쉬었음'인 사람만
(육아·가사·통학·취업준비·심신장애와 구분되는 순수 쉬었음) → 표본 1,062명.
**KPI** · *규모(만 명)* = 가중치(`weight_person`) 합(모집단 환산), *비율(%)* = 가중 비율.
**왜 가중?** 표본 1명이 모집단에서 대표하는 인원이 달라, 가중해야 전국 대표값이 된다.
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
        fig = charts.line_stacked_trends(
            merged, x="year", y_top="value_unemp", y_bottom="value_rest",
            name_top="청년 실업률 (%)", name_bottom="청년 쉬었음 인구 (천 명)",
            title="청년(15–29) 실업률 vs 쉬었음 인구 추이",
            top_title="실업률(%)", bottom_title="쉬었음(천 명)",
            color_top="#F58518", color_bottom="#E45756",
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("출처: 경제활동인구조사(EAPS) 집계표. 쉬었음 시계열은 2003년부터 제공.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"EAPS 데이터를 불러오지 못했습니다: {exc}")

    with st.expander("🌐 국제·구조 맥락 — 청년 NEET (OECD / 고용정보원)", expanded=False):
        show_fig("00_neet_oecd_background.png",
                 "한국은 OECD 중 2014 대비 NEET가 증가한 유일국, 그중 '비구직형'만 증가(질적 고착).")
    method_note(
        """
**자료** · 통계청 EAPS **공식 집계표**(개인 원자료 아님)를 연도×지표 long으로 변환(`eaps_labor_status_summary`).
청년 **15–29세** 행만 사용.
**왜 위·아래 2단인가** · 실업률(%)과 쉬었음 인구(천 명)는 **단위가 달라** 한 축에 겹치면 헷갈린다.
두 세로축 모두 **0부터** 고정해 기울기 과장을 막았다.
**읽는 법** · 위(실업률)는 2020년 이후 **하락**, 아래(쉬었음)는 **계속 증가** → "실업률만 보면 놓치는 청년층".
**외부보강** · 고용정보원(2025) NEET 재산출로 국제 맥락 확인(`docs/external_data_references.md` §2).
"""
    )


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
    st.markdown(f"- **쉬었음 vs 실업자** · 삶 만족도: {_badge(b1)}")
    method_note(
        """
**집단 정의** · `취업자`·`실업자`(구직 중 미취업)·`쉬었음`·`비경활(기타)`(육아·가사·통학 등).
**값** · 집단별 **가중 평균**(웰빙)·**가중 비율**(취약지표).
**검정** · 연속변수는 분포 가정 없는 **Mann-Whitney U**, 효과크기(r) 병기.
**왜 막대 차이가 작아 보이나** · 삶 만족도는 0–10 척도라 실제 차이가 작다. 표본이 커 통계적으론 유의할 수 있어 **p·효과크기**를 함께 본다.
**핵심** · 실업자가 웰빙 최저, 쉬었음은 그 위 → **쉬었음 ≠ 실업자**.
"""
    )


# ======================================================================
# S3 무엇으로 버티나 (가족 중심)
# ======================================================================
elif section == SECTIONS[3]:
    st.header("쉬어도 생활비는 든다 — 무엇으로 버티나")
    st.markdown("쉬었음 청년의 **다수(약 85%)는 가족 비공식 지원망**으로 생활비를 버틴다. "
                "그래서 평균 경제지표만 보면 '괜찮아 보이는' 착시가 생기고, 이 평균이 **내부 격차를 가린다.**")

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

    with st.expander("🔬 보강실험 — '가족 도움 가능'이 곧 안전은 아니다(안전망 등급별 웰빙)", expanded=False):
        show_fig("20_rested_safety_tiers.png",
                 "견고 6.57 > 조건부 6.32 > 취약 6.01 (Kruskal-Wallis p=0.035). 도움가능 응답만으론 안전 단정 불가.")
    method_note(
        """
**설문 문항** · "생활비 부족 시 도움받을 수 있는 곳"(복수응답): 가족·지인·공공·민간·없음.
**막대** · 각 보기 '해당' 가중 비율(%). 쉬었음(빨강) vs 취업자(파랑).
**도넛** · 쉬었음을 상호배타 3유형(없음 > 공식 > 비공식 우선순위)으로 묶은 모집단 구성비(서술용).
**핵심** · 약 85%가 가족·지인(비공식)에 의존 → 버티는 방식이 **가족 한 곳에 쏠림**. 그 망이 얇은 일부가 위험군 후보.
"""
    )


# ======================================================================
# S4 ★핵심★ 취약의 핵심 축 = 고립
# ======================================================================
elif section == SECTIONS[4]:
    st.header("★ 취약을 가르는 축 = 사회적 고립 ★")
    st.markdown("쉬었음 내부를 갈라보면, 취약을 결정하는 건 부채·소득이 아니라 **'고립'**. "
                "고립된 청년은 삶 만족이 급락하고, 도움받을 곳도 없는 **이중고**다.")

    show_fig("21_rested_isolation.png",
             "고립 vs 비고립 — 웰빙·지원망 이중고 (Fisher 정확검정).")

    # 인앱 재계산: 고립 vs 비고립 핵심 수치
    r2 = rested.copy()
    r2["고립"] = pd.to_numeric(r2["isolation_flag"], errors="coerce").map({1: "고립", 0: "비고립"})
    r2 = r2[r2["고립"].notna()]
    means = _weighted_means_by_group(
        r2, "고립", {"life_satisfaction": "삶 만족도", "happiness": "행복감"}, ["비고립", "고립"])
    figm = charts.grouped_bar(
        means, x="지표", y="값", color="집단", title="고립 여부별 주관 웰빙 (가중 평균, 0–10)",
        color_map=ISO_COLORS, category_orders={"집단": ["비고립", "고립"]},
        x_title="", y_title="평균(0–10)", text_format=".2f")
    st.plotly_chart(figm, width="stretch")

    b_ls = queries.mann_whitney_compare(r2, "고립", "life_satisfaction", "고립", "비고립")
    st.markdown(f"- **고립 vs 비고립** · 삶 만족도: {_badge(b_ls)}")
    try:
        ct = pd.crosstab(r2["고립"], pd.to_numeric(r2["no_help_flag"], errors="coerce"))
        if ct.shape == (2, 2):
            odds, p_f = stats.fisher_exact(ct.values)
            iso_rate = queries.weighted_share(r2[r2["고립"] == "고립"], "no_help_flag")["비율_가중(%)"]
            non_rate = queries.weighted_share(r2[r2["고립"] == "비고립"], "no_help_flag")["비율_가중(%)"]
            st.markdown(f"- **'도움없음' 비율** · 비고립 {non_rate}% → 고립 {iso_rate}% · "
                        f"**Fisher 정확검정 p={p_f:.2e}, 오즈비≈{odds:.1f}배** "
                        f"{'✅ 유의' if p_f < 0.05 else '➖ 비유의'}")
    except Exception:  # noqa: BLE001
        pass
    method_note(
        """
**고립 정의** · 외출빈도가 매우 낮은(거의 외출 안 함) 응답을 고립으로 표시(`isolation_flag`, 쉬었음 내 약 3.9%).
**왜 '고립'만 떼나** · 위험요인을 뭉치면(등급화·총점) 신호가 약해진다(보강실험·스펙트럼 실패).
요인을 **분리**해 보면 부채는 웰빙을 거의 안 낮추고, **고립이 웰빙을 크게 가른다.**
**검정** · 웰빙은 Mann-Whitney U(효과크기 r), 소표본 2×2(고립×도움없음)는 **Fisher 정확검정**(카이제곱 근사 대신).
**핵심** · 고립자는 삶만족 r≈-0.47(큰 효과), '도움없음' 오즈비 약 5.8배 → **취약의 핵심 축 = 관계 단절**.
"""
    )


# ======================================================================
# S5 고립의 심도 — 공식 은둔 용량반응
# ======================================================================
elif section == SECTIONS[5]:
    st.header("고립의 심도 — 공식 '은둔' 지표와 외부 수렴")
    st.markdown("파생 고립지표를 넘어, **공식 '은둔 지속기간' 변수**로 보면 은둔이 길수록 삶 만족이 "
                "**단조 하락**(용량반응)하고, 정부 공식조사와 **수치가 수렴**한다.")

    show_fig("23_rested_seclusion_doseresponse.png",
             "좌: 은둔 기간↑ → 삶만족↓ (6.70→3.75). 우: 복지부 2023 고립·은둔 조사(3.7 vs 6.7)와 수렴.")
    method_note(
        """
**변수** · 청년삶 2024 공식 `seclusion_duration`(은둔 지속기간). 가중 평균 삶만족 + Spearman 추세.
**왜 강한가** · binary 고립(외출 7~8점, n=41)보다 **풍부**(은둔 경험자 n=226)하고 **단계적 하락**(용량반응)이 보인다.
**외부 수렴** · 복지부 2023 고립·은둔 청년 실태조사(삶만족 3.7 vs 전체청년 6.7)와 우리 양끝(6.70·3.75)이 거의 일치
→ 미시결과의 **외적 타당도**(소표본 한계를 외부 공식통계로 방어).
**한계** · 장기은둔군 소표본(n≤20), 2024 단년(2022엔 변수 부재 → 연도비교 불가).
"""
    )


# ======================================================================
# S6 ★전국 일반화 (KGSS) — KOSSDA 기둥★
# ======================================================================
elif section == SECTIONS[6]:
    st.header("★ 전국 일반화 (KGSS) — '쉬었음'이 아니라 '고립'이 웰빙을 가른다 ★")
    st.markdown("청년삶은 표본이 **전원 쉬었음**이라 '고립 vs 노동상태' 직접대조가 불가능하다. "
                "**KGSS 전국 표본**이 이를 대신한다 — 취업 여부로는 행복이 거의 안 갈리고, **고립 여부로는 크게 갈린다.**")

    k = load_kgss_summary()
    show_fig("24_kgss_isolation_vs_employment.png",
             ("좌: 고립 격차 vs 취업 격차. 우: 고립 페널티는 취업·미취업 양쪽 일관."
              if k is None else
              f"좌: 고립 격차 Δ{k['d_iso']:.3f}{k['iso_star']} vs 취업 격차 Δ{k['d_emp']:.3f} {k['emp_star']}"
              f"(약 {k['ratio']:.0f}배). 우: 고립 페널티는 취업·미취업 양쪽 일관."))

    if k is None:
        st.info("KGSS 요약 파일이 없습니다. `python scripts/kgss_isolation.py` 실행 후 다시 보세요.", icon="🧮")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("고립 행복 격차 Δ", f"{k['d_iso']:.3f}", f"p={k['p_iso']:.1e} {k['iso_star']}")
        c2.metric("취업 행복 격차 Δ", f"{k['d_emp']:.3f}", f"p={k['p_emp']:.2f} {k['emp_star']}")
        c3.metric("고립 격차 / 취업 격차", f"약 {k['ratio']:.0f}배", "고립이 압도")
        st.markdown(
            f"""
- **데이터** · 한국종합사회조사(**KGSS**) 2021·23·25 통합 **N={int(k['n']):,}**, 성균관대 SRC / **KOSSDA 소장**. 가중 FINALWT.
- **변수** · 행복 `HAPPINSS`(역코딩 1~5, 높을수록 행복), 고립=믿는 친구 0명 `BESTFRND`, 취업 `EMPLY`. 검정 Mann-Whitney U.
- **결론** · 고립 페널티는 **취업군(Δ={k['pen_emp']:.3f})·미취업군(Δ={k['pen_nonemp']:.3f}) 양쪽에서 거의 동일**
  → 고립 효과는 **노동시장 상태와 독립**. 청년삶의 피벗('고립이 웰빙을 가른다')이 **전국·독립표본에서 재현**된다.
- **공모전 의의** · KOSSDA 소장(SRC 기탁) 데이터를 실질 분석으로 활용 → 필수조건 충족 + **「KGSS상」 트랙** 자격.

<small>※ 위 수치는 `scripts/kgss_isolation.py`가 KGSS 원자료에서 계산해 저장한
`data/processed/kgss_isolation_summary.csv`를 읽어 표시(하드코딩 아님).</small>
""",
            unsafe_allow_html=True,
        )

    with st.expander("📎 부록 — 친구 수 용량반응 / 외로움→우울 수렴", expanded=False):
        show_fig("25_kgss_friends_doseresponse.png", "믿는 친구 수↑ → 행복↑(0명에서 절벽). KGSS 2021·23·25.")
        show_fig("26_kgss_loneliness_depression_2012.png", "외로움↑ → 우울↑(MWU p<1e-23). 다른 해·다른 측정 수렴(2012).")
    with st.expander("📎 부록 — KLIPS(KOSSDA 보조검증): 비취업 청년 가구부채", expanded=False):
        show_fig("09_klips_supplement.png",
                 "KLIPS 2023 청년: 비취업 가구부채 54.1% vs 취업 43.6%(카이제곱 p=0.017). 방향만 참고.")
    method_note(
        """
**왜 KGSS인가** · 청년삶 표본은 전원 쉬었음이라 '고립 vs 취업' 대조가 불가능 → 전국 성인표본 KGSS로 대신한다.
**그림 읽는 법(좌)** · 막대는 두 가지로 행복을 갈랐을 때의 격차 Δ. 취업으로는 거의 안 갈리고(회색, n.s.),
고립으로는 크게 갈린다(빨강, ***). **(우)** 고립 페널티(비고립-고립)가 취업·미취업 양쪽에서 거의 같다 = 고립은 독립적으로 작동.
**한계(D16)** · KGSS 청년 부분표본은 과소 → 청년 시계열은 단정하지 않고 **전국 성인 일반화까지만** 주장.
**KOSSDA 인용** · 김지범. 한국종합사회조사, 2003-2025 [누적자료]. SRC/KOSSDA, https://doi.org/10.22687/KOSSDA-A1-CUM-0074-V1.
"""
    )


# ======================================================================
# S7 재현성·추세 (2022 ↔ 2024)
# ======================================================================
elif section == SECTIONS[7]:
    st.header("재현성·추세 — 2022 vs 2024")
    st.markdown("같은 정의·같은 파생규칙으로 **2022 청년삶**을 처리해, 2024 결과가 "
                "**우연이 아니라 재현·악화되는 추세**임을 확인한다.")
    try:
        d22, d24 = load_year(2022), load_year(2024)
        r22 = d22[d22["is_rested"] == 1].copy()
        r24 = d24[d24["is_rested"] == 1].copy()

        rows = []
        for yr, d in (("2022", d22), ("2024", d24)):
            s = queries.weighted_share(d, "is_rested")
            rows.append({"연도": yr, "값": s["비율_가중(%)"]})
        size_df = pd.DataFrame(rows)
        fig_s = charts.grouped_bar(
            size_df, x="연도", y="값", color="연도",
            title="청년 대비 쉬었음 비중 (가중 %) — 2022 vs 2024",
            color_map=YEAR_COLORS, category_orders={"연도": ["2022", "2024"]},
            x_title="", y_title="비중(%)", text_format=".1f")
        st.plotly_chart(fig_s, width="stretch")

        both = pd.concat([r22, r24], ignore_index=True)
        flags = {"no_help_flag": "지원망 없음", "has_debt": "부채 보유",
                 "has_interest": "이자 부담"}
        rows, notes = [], []
        for col, label in flags.items():
            w22 = queries.weighted_share(r22, col)["비율_가중(%)"]
            w24 = queries.weighted_share(r24, col)["비율_가중(%)"]
            rows += [{"지표": label, "연도": "2022", "값": w22},
                     {"지표": label, "연도": "2024", "값": w24}]
            t = queries.chi_square_compare(both, "survey_year", col, 2022, 2024)
            sig = "✅유의" if (t.get("p") is not None and t["p"] < 0.05) else "➖비유의"
            notes.append(f"- **{label}** · 2022 {w22}% → 2024 {w24}% · "
                         + (f"p={t['p']:.3g} {sig}" if t.get("p") is not None else "표본부족"))
        vdf = pd.DataFrame(rows)
        fig_v = charts.grouped_bar(
            vdf, x="지표", y="값", color="연도",
            title="쉬었음 내부 취약지표 (가중 %) — 2022 vs 2024",
            color_map=YEAR_COLORS, category_orders={"연도": ["2022", "2024"]},
            x_title="", y_title="보유율(%)", text_format=".1f")
        st.plotly_chart(fig_v, width="stretch")
        st.markdown("\n".join(notes))

        st.subheader("사적 안전망이 얇아진다")
        show_fig("17b_rested_safety_net_2022_2024.png",
                 "가족 도움 95→85%, 도움없음 3.5→8.4%(약 2배). 제도(공공·민간)는 3~4%로 공백 지속.")
        method_note(
            """
**왜 2022를 보나** · 한 해(2024)만으론 우연일 수 있어, **동일 정의·동일 전처리**로 2022를 처리해 방향 재현을 본다
(`build_youth_2022_analysis`, `scripts/compare_years.py`).
**검정** · 연도 간 비율 차이는 카이제곱(비가중). 효과크기는 작아도 방향 일관.
**핵심** · 쉬었음 비중↑(5.2→7.2%) + 내부 취약(지원망없음·부채·이자) 모두↑·유의 + 가족 버팀목↓
→ 평균 웰빙은 그대로인데(6.41→6.44) **내부 격차가 깊어졌다.**
**정직한 한계** · 고립지표는 외출빈도 척도가 2022(1~7)·2024(1~8)로 달라 **연도 직접비교에서 제외**(D9).
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
- **다수는 가족지원망(약 85%)** 으로 버티지만, 그 평균이 내부 격차를 가린다.
- **취약을 가르는 축은 돈이 아니라 '고립'** — 고립 청년은 삶 만족 급락(r≈-0.47),
  도움없음 약 5.8배(Fisher). 공식 '은둔 기간'도 길수록 삶만족 단조 하락(외부조사와 수렴).
  - (`도움없음` 약 {no_help['모집단추정(명)']/10000:.1f}만 명, {no_help['비율_가중(%)']}%)
- **전국(KGSS) 재현**: 취업 여부보다 **고립**이 행복을 약 14배 더 가른다(취업·미취업 무관).
- **2022→2024**: 쉬었음 규모↑ + 내부 취약↑ + 가족 버팀목↓(평균은 그대로 = 내부격차 심화).

### 정책 함의
- '쉬었음'을 일자리 미스매치로만 보지 말고, **고립 여부로 우선 타게팅.**
- 사각지대(고립·도움없음)는 소득지원보다 **사회적 연결·접촉 기반 개입**(관계망 재건)이 핵심.
- 가족 의존이 얇아지는 추세 → **공적 안전망이 가족을 보완**해야.

### 선행연구와의 차별점
- 2025 수상작('캥거루 청년')은 *거주 독립·심리자본*. 본 연구는 ① 대상 **'쉬었음'(노동시장 밖)**,
  ② 축 **사회적 고립(관계)**, ③ **KGSS 전국 일반화** 로 구별된다.
"""
    )
    st.caption("※ 한계: 소표본 하위집단(고립·도움없음)은 효과크기로 보고·경향 해석. 데이터 간 개인결합 불가(층위별 근거 결합). "
               "관찰연구라 인과 아님. KGSS는 전국 성인 일반화까지만 주장.")

st.divider()
st.caption("표시 수치는 청년삶 2024·2022·EAPS·KGSS·KLIPS 실데이터에서 계산. © 2026 경영정보처리론 · KOSSDA 공모전")
