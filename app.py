"""청년 '쉬었음' 집단의 생활안전망 격차와 고립 · Streamlit 대시보드.

분석 흐름(S0~S9): 배경 → 생활 유지(보유율·가족) → H1~H4 → 고립 → KGSS → 2022↔2024 → 결론.
데이터: 청년삶 2024·2022, EAPS, KGSS, KLIPS.
쉬었음 내부(N=1,062) 분석은 비가중, 모집단 규모만 가중. 수치는 DB 실데이터에서 계산.

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
# 생활안전망 6유형 표시 순서·색 (우선순위 규칙 분류)
TYPE6_ORDER = ["가족완충형", "금융부담형", "취약잠재형", "고립위험형", "대체지원형", "공공지원형"]
TYPE6_COLORS = {
    "가족완충형": "#4C78A8", "금융부담형": "#F58518", "취약잠재형": "#9D9D9D",
    "고립위험형": "#E45756", "대체지원형": "#B279A2", "공공지원형": "#72B7B2",
}
RISK_ORDER = ["저위험", "중위험", "고위험"]
RISK_COLORS = {"저위험": "#9D9D9D", "중위험": "#F58518", "고위험": "#E45756"}


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
    "S2 · 무엇으로 버티나 (보유율)",
    "S3 · 가족 안전망 격차 (H1·H2)",
    "S4 · 가족이 없다면 (도달률)",
    "S5 · 위험 중첩과 6유형",
    "S6 · ★취약의 가장 깊은 곳 = 고립★",
    "S7 · ★전국 일반화 (KGSS)★",
    "S8 · 재현성·추세 (2022↔2024)",
    "S9 · 결론 · 함의",
]
section = st.sidebar.radio("분석 흐름", SECTIONS)
st.sidebar.caption("쉬었음 내부(N=1,062) 분석=비가중 / 모집단 규모 환산=가중")
st.sidebar.markdown("---")
st.sidebar.caption("📄 분석 설계: `docs/analysis_flow.md`\n\n🟢 PPT 초안: `발표_초안.md`")


# ======================================================================
# S0 개요
# ======================================================================
if section == SECTIONS[0]:
    st.header("개요 · 핵심 요약")
    rest_share = queries.weighted_share(df, "is_rested")
    no_help = queries.weighted_share(rested, "no_help_flag")
    iso = queries.weighted_share(rested, "isolation_flag")
    risk_pct = (pd.to_numeric(rested.get("risk_score"), errors="coerce") >= 2).mean() * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("쉬었음 청년 규모(가중)", f"약 {rest_share['모집단추정(명)']/10000:.0f}만 명",
              f"{rest_share['비율_가중(%)']}%")
    c2.metric("쉬었음 표본", f"{len(rested):,}명")
    c3.metric("위험요인 2개 이상 중첩", f"{risk_pct:.1f}%", "위험점수 0–5 기준")
    c4.metric("도움받을 곳 '없음'", f"{no_help['비율_가중(%)']}%",
              f"약 {no_help['모집단추정(명)']/10000:.1f}만 명")

    st.markdown(
        """
**한 줄 메시지** · "'쉬었음' 청년은 단일 집단이 아니다 — **기대는 안전망(가족·공공·금융)의 종류에 따라
분화된 집단**이며, 그 격차의 가장 깊은 곳에 **고립된 청년**이 있다. 이는 전국 데이터(KGSS)에서도
**취업 여부보다 고립이 웰빙을 가른다**로 재현된다."

**분석 흐름(좌측 S1→S9)**
1. **배경** — 실업률은 안정·하락하는데 노동시장 밖 **'쉬었음'은 증가**(사각지대). 쉬었음 ≠ 실업자.
2. **무엇으로 버티나** — 부채·이전소득은 **보유율·보유자 중앙값**으로 봐야 한다(평균 착시).
   다수(약 85%)는 **가족**으로 버틴다.
3. **가족 안전망 격차(H1·H2)** — 부모 비동거 청년의 부채 보유율은 동거의 약 2배.
   가족지원 유무는 생활비 수준과도 유의하게 연관.
4. **가족이 없다면(H3)** — 가족지원 부재 청년의 절반 이상은 **어디에도 도움을 청할 곳이 없다**(도달률 공백).
5. **위험 중첩·6유형(H4)** — 위험요인은 소수에 중첩되고, 안전망 유형으로 구조화된다.
6. ★ **가장 깊은 곳 = 사회적 고립** — 돈(부채)보다 **관계 단절**이 웰빙을 가른다.
   공식 '은둔 기간'도 길수록 삶만족 단조 하락.
7. ★ **전국 일반화(KGSS)** — 취업이 아니라 **고립**이 행복을 가른다(약 14배).
8. **재현·악화** — 2022→2024 쉬었음↑·내부 취약↑·가족 버팀목↓.
9. **결론** — **유형별 차등 정책** + 일자리를 넘어 **고립 해소·관계망 재건**.
"""
    )
    st.info("좌측 사이드바에서 S1→S9 순서로 흐름을 따라가세요.", icon="🧭")
    method_note(
        """
**데이터** · 청년삶실태조사 2024 응답자 15,098명(만 19–34세).
**'쉬었음' 정의** · 경제활동상태=비경제활동 **그리고** 지난주 주된활동='쉬었음'인 사람만
(육아·가사·통학·취업준비·심신장애와 구분되는 순수 쉬었음) → 표본 1,062명.
**KPI** · *규모(만 명)* = 가중치(`weight_person`) 합(모집단 환산), *비율(%)* = 가중 비율.
단, **위험군 비율(23.0%)·쉬었음 내부 분석은 비가중**(중간발표·소논문 수치와 동일 기준).
**위험점수(0–5)** · 부모 비동거 + 가족지원 없음 + 도움망 없음 + 부채 보유 + 이자 부담의 합.
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

    st.subheader("쉬었음은 누구인가 — 실업자와 다르다")
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
# S2 무엇으로 버티나 — 보유율·보유자 중앙값 + 가족 편중
# ======================================================================
elif section == SECTIONS[2]:
    st.header("쉬어도 생활비는 든다 — 무엇으로 버티나")
    st.markdown("부채·이자·이전소득은 **0인 응답자가 다수(0-팽창)** 라서 평균이 소수 고액 사례에 왜곡된다. "
                "그래서 **보유율 + 보유자 중앙값**으로 본다. 그리고 생활을 받치는 망은 **가족 한 곳에 쏠려 있다.**")

    st.subheader("자원·부담 변수의 보유율과 보유자 중앙값 (쉬었음, 비가중)")
    hold = queries.holding_summary(rested, {
        "debt_total": "부채 총액",
        "interest_monthly": "월평균 이자",
        "transfer_private": "사적 이전소득(연)",
        "transfer_public": "공적 이전소득(연)",
    })
    st.dataframe(hold, hide_index=True, width="stretch")
    if not hold.empty:
        debt_row = hold[hold["변수"] == "부채 총액"]
        if not debt_row.empty:
            st.markdown(
                f"- 부채는 **{debt_row.iloc[0]['보유율(%)']}%만 보유**하지만, 보유자 중앙값은 "
                f"**{debt_row.iloc[0]['보유자 중앙값(만원)']:,.0f}만 원** → 부담이 **특정 집단에 집중**된다.")

    st.subheader("생활비 부족 시 도움 가능한 곳 — 가족 편중")
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

    with st.expander("🔬 보강실험 — '가족 도움 가능'이 곧 안전은 아니다(안전망 등급별 웰빙)", expanded=False):
        show_fig("20_rested_safety_tiers.png",
                 "견고 6.57 > 조건부 6.32 > 취약 6.01 (Kruskal-Wallis p=0.035). 도움가능 응답만으론 안전 단정 불가.")
    method_note(
        """
**0-팽창 처리** · 부채·이자·이전소득은 평균을 보고하지 않는다.
**보유율**(값>0 비율)과 **보유자 중앙값**(값>0 응답자 내 중앙값)을 병기 → 평균 착시 제거.
**단위 주의** · 이전소득은 **연** 단위, 생활비·이자는 **월** 단위(비교 시 환산 필요).
**설문 문항** · "생활비 부족 시 도움받을 수 있는 곳"(복수응답): 가족·지인·공공·민간·없음.
**핵심** · 다수가 가족·지인(비공식)에 의존 → 버티는 방식이 **가족 한 곳에 쏠림**.
그 망이 얇은 청년이 어떤 처지인지는 S3·S4에서 검정으로 확인한다.
"""
    )


# ======================================================================
# S3 가족 안전망 격차 — H1(부모동거×부채) · H2(가족지원×생활비)
# ======================================================================
elif section == SECTIONS[3]:
    st.header("가족은 얼마나 강력한 안전망인가 — H1 · H2")
    st.markdown("가족 자원의 유무는 쉬었음 청년의 **부채 위험·생활 수준**과 직결된다. "
                "p값과 함께 **효과크기**도 함께 보고한다.")

    r3 = rested.copy()
    r3["가족지원"] = pd.to_numeric(r3.get("family_help_flag"), errors="coerce").map(
        {1: "가족 도움 가능", 0: "가족 도움 없음"})

    st.subheader("H1 · 부모 비동거 청년은 부채 위험이 높다")
    h1_rate = queries.chi_square_compare(r3, "parents_label", "has_debt", "부모동거", "비동거")
    c1, c2 = st.columns(2)
    c1.metric("부모 동거 부채 보유율", f"{h1_rate.get('비율A(%)')}%", f"n={h1_rate.get('n_A')}")
    c2.metric("부모 비동거 부채 보유율", f"{h1_rate.get('비율B(%)')}%", f"n={h1_rate.get('n_B')}",
              delta_color="inverse")
    st.markdown(f"- **부채 보유율 차이** ({h1_rate.get('검정', '카이제곱')}, χ²={h1_rate.get('chi2')}): {_badge(h1_rate)}")
    h1_amt = queries.mann_whitney_compare(r3, "parents_label", "debt_total", "부모동거", "비동거")
    st.markdown(f"- **부채 총액 분포 차이** (Mann-Whitney U): {_badge(h1_amt)}")
    debt_pos = r3[pd.to_numeric(r3["debt_total"], errors="coerce") > 0]
    fig_h1 = charts.box_chart(debt_pos, x="parents_label", y="debt_total",
                              title="부모 동거 여부 × 부채 총액 (부채 보유자만, 만원)")
    st.plotly_chart(fig_h1, width="stretch")

    st.subheader("H2 · 가족지원 가용성은 생활비 수준과 연관된다")
    h2 = queries.mann_whitney_compare(r3, "가족지원", "living_cost", "가족 도움 가능", "가족 도움 없음")
    st.markdown(
        f"- **월 생활비 중앙값** · 가족 도움 가능 {h2.get('중앙값_A')}만 원 vs "
        f"없음 {h2.get('중앙값_B')}만 원 (Mann-Whitney U): {_badge(h2)}")
    fig_h2 = charts.box_chart(r3[r3["가족지원"].notna()], x="가족지원", y="living_cost",
                              title="가족지원 여부 × 월 평균 총생활비 (만원)")
    st.plotly_chart(fig_h2, width="stretch")
    method_note(
        """
**H1** · 부모 동거(1) vs 비동거 × 부채 보유(>0). 보유율 차이는 **카이제곱**(2×2 기대빈도<5면 Fisher 자동 전환),
금액 분포 차이는 **Mann-Whitney U**(0-팽창·비대칭 분포라 t검정 부적합). 박스플롯은 보유자만 표시(0 다수가 분포를 가리므로).
**H2** · 가족 도움 가능 여부 × 월 생활비. 중앙값과 MWU p를 보고.
**효과크기** · 검정마다 rank-biserial r / Cramér's V 병기(표본이 크면 작은 차이도 유의하므로 크기로 판단).
**해석 한계** · 횡단면 연관이지 인과가 아니다. 비동거가 부채를 '만든다'고 말할 수 없다.
"""
    )


# ======================================================================
# S4 가족이 없다면 — H3 도달률(coverage)
# ======================================================================
elif section == SECTIONS[4]:
    st.header("가족이 없다면 무엇으로 버티는가 — H3 도달률")
    st.markdown("가족지원이 없는 청년에게 **공공 안전망이 그 공백을 메우는지**를, 선택편향에 취약한 상관 대신 "
                "**도달률(coverage)** 로 식별한다.")

    fam = pd.to_numeric(rested.get("family_help_flag"), errors="coerce")
    no_family = rested[fam == 0]
    flag_labels = {"help_living_acq": "지인", "help_living_public": "공공기관",
                   "help_living_private": "민간기관", "help_living_none": "도움받을 곳 없음"}
    cov_nf = queries.coverage_rates(no_family, flag_labels)
    cov_all = queries.coverage_rates(rested, flag_labels)
    cov_nf["집단"] = f"가족지원 없음 (n={len(no_family)})"
    cov_all["집단"] = f"쉬었음 전체 (n={len(rested)})"
    cov = pd.concat([cov_all, cov_nf], ignore_index=True)
    fig_cov = charts.grouped_bar(
        cov, x="안전망", y="도달률(%)", color="집단",
        title="대체 안전망 도달률 — 쉬었음 전체 vs 가족지원 부재 집단 (비가중 %)",
        color_map={cov_all["집단"].iloc[0]: "#9D9D9D", cov_nf["집단"].iloc[0]: "#E45756"},
        x_title="", y_title="도달률(%)", text_format=".1f")
    st.plotly_chart(fig_cov, width="stretch")

    none_nf = cov_nf[cov_nf["안전망"] == "도움받을 곳 없음"]
    none_all = cov_all[cov_all["안전망"] == "도움받을 곳 없음"]
    pub_nf = cov_nf[cov_nf["안전망"] == "공공기관"]
    if not none_nf.empty and not none_all.empty and not pub_nf.empty:
        ratio = none_nf.iloc[0]["도달률(%)"] / none_all.iloc[0]["도달률(%)"] if none_all.iloc[0]["도달률(%)"] else None
        st.markdown(
            f"- 가족지원이 없는 청년 {len(no_family)}명 중 **'도움받을 곳이 전혀 없다' {none_nf.iloc[0]['도달률(%)']}%** "
            f"(전체 {none_all.iloc[0]['도달률(%)']}% 대비 약 **{ratio:.0f}배**), "
            f"**공공기관 도달률은 {pub_nf.iloc[0]['도달률(%)']}%** 에 그침 → 공공이 가족 공백을 대체하지 못한다 (**H3 지지**).")
    method_note(
        """
**왜 도달률인가** · 공적 이전소득×부채 상관으로 '공공 안전망 효과'를 판단하면 안 된다.
공적지원은 취약층에 **표적 지급**되므로 수급↔부채에 **역방향 선택편향**이 있어 인과 해석 불가.
대신 가족지원 부재 집단에서 **대체 안전망(지인/공공/민간) 도움 가능률과 '도움없음' 비율**을 본다 — 선택편향이 없다.
**값** · 비가중 비율. 가족지원 부재 집단은 소표본이므로 n 병기.
**핵심** · 가족이 끊긴 청년의 절반 이상이 어떤 공식·비공식 안전망에도 연결되지 못함 → **공공 안전망의 공백**.
"""
    )


# ======================================================================
# S5 위험 중첩과 생활안전망 6유형 — H4
# ======================================================================
elif section == SECTIONS[5]:
    st.header("누가 가장 위험한가 — 위험 중첩과 6유형 (H4)")
    st.markdown("위험요인(부모비동거·가족지원없음·도움망없음·부채·이자)은 고르게 분포하지 않고 "
                "**소수에 중첩**되며, 청년들은 **기대는 안전망의 종류에 따라 6개 유형으로 분화**된다.")

    r5 = rested.copy()
    r5["risk_score"] = pd.to_numeric(r5.get("risk_score"), errors="coerce")
    risk_pct = float((r5["risk_score"] >= 2).mean() * 100)

    c1, c2 = st.columns([1, 2])
    with c1:
        st.plotly_chart(charts.gauge(risk_pct, title="위험군(위험점수 ≥ 2) 비율", max_value=100),
                        width="stretch")
    with c2:
        dist = (r5.groupby(["risk_score", "risk_level"]).size()
                .reset_index(name="인원"))
        fig_d = charts.grouped_bar(
            dist, x="risk_score", y="인원", color="risk_level",
            title="위험점수(0–5) 분포", barmode="stack",
            color_map=RISK_COLORS, category_orders={"risk_level": RISK_ORDER},
            x_title="위험점수", y_title="인원(명)")
        st.plotly_chart(fig_d, width="stretch")

    st.subheader("생활안전망 6유형 — 규모와 프로파일")
    t6 = r5["safety_net_type6"].value_counts().reset_index()
    t6.columns = ["유형", "인원"]
    st.plotly_chart(
        charts.treemap(t6, path_col="유형", value_col="인원",
                       title="생활안전망 유형별 규모 (쉬었음 N=%d)" % len(r5),
                       color_map=TYPE6_COLORS),
        width="stretch")

    prof_rows = []
    for t, sub in r5.groupby("safety_net_type6"):
        prof_rows.append({
            "유형": t,
            "인원(명)": len(sub),
            "비율(%)": round(len(sub) / len(r5) * 100, 1),
            "평균 생활비(만원/월)": round(pd.to_numeric(sub["living_cost"], errors="coerce").mean(), 1),
            "부채 보유율(%)": round(queries.holding_rate(sub["debt_total"]) * 100, 1),
            "이자 부담률(%)": round(queries.holding_rate(sub["interest_monthly"]) * 100, 1),
            "평균 위험점수": round(pd.to_numeric(sub["risk_score"], errors="coerce").mean(), 2),
            "평균 삶만족(0–10)": round(pd.to_numeric(sub["life_satisfaction"], errors="coerce").mean(), 2),
        })
    prof = pd.DataFrame(prof_rows).set_index("유형").reindex(TYPE6_ORDER).reset_index()
    st.dataframe(prof, hide_index=True, width="stretch")

    st.subheader("유형 × 주관 웰빙")
    sat = prof[["유형", "평균 삶만족(0–10)"]].dropna()
    fig_sat = charts.grouped_bar(
        sat, x="유형", y="평균 삶만족(0–10)", color="유형",
        title="유형별 평균 삶 만족도 (비가중, 0–10)",
        color_map=TYPE6_COLORS, category_orders={"유형": TYPE6_ORDER},
        x_title="", text_format=".2f")
    fig_sat.update_layout(showlegend=False)
    st.plotly_chart(fig_sat, width="stretch")
    iso_sat = prof.loc[prof["유형"] == "고립위험형", "평균 삶만족(0–10)"]
    fam_sat = prof.loc[prof["유형"] == "가족완충형", "평균 삶만족(0–10)"]
    if not iso_sat.empty and not fam_sat.empty:
        st.markdown(
            f"- **고립위험형은 자원만 없는 게 아니라 웰빙도 최하위권이다**"
            f"(평균 삶만족 {iso_sat.iloc[0]} vs 가족완충형 {fam_sat.iloc[0]} — 대체지원형과 함께 가장 낮은 축). "
            "이 유형은 S6에서 다루는 **고립**과 가장 가깝다.")
    method_note(
        """
**위험점수(0–5)** · ①부모 비동거 ②가족지원 없음 ③도움망 없음 ④부채 보유 ⑤이자 부담의 합.
위험수준 = 저(0–1)/중(2–3)/고(4–5). 평균 점수는 0-편중으로 과소표시되므로 **위험군(≥2) 비율**을 게이지로 본다.
**6유형(우선순위 규칙)** · 도움망 없음 → 고립위험형 / 부채·이자·생활비부채 → 금융부담형 / 가족지원+부모동거 → 가족완충형 /
공공기관 → 공공지원형 / 지인·민간 → 대체지원형 / 그 외 → 취약잠재형. **연구자 정의 규칙 기반 지표**라
가중치·기준에 따라 결과가 달라질 수 있음(민감도 분석 과제).
**웰빙 연결** · 유형별 삶만족을 함께 보면 자원 격차가 **주관적 삶의 질 격차**로 이어지는지 확인할 수 있다.
유형 간 삶만족 분포 차이는 전체 검정(Kruskal-Wallis)에서 유의하나, **쌍별 비교는 Holm 보정 후
유의 수준에 도달하지 못함**(소표본 유형 다수) → 유형×웰빙 연결은 **경향 수준으로 제한 해석**.
**강건성** · 위험점수 leave-one-out·임계값 변경, 유형 우선순위 스왑, 핵심 수치 가중 재산출은
`scripts/robustness.py` → `outputs/robustness_summary.md` 참조 (가중 적용 시에도 H1·H2·H3 방향 유지).
"""
    )


# ======================================================================
# S6 ★핵심★ 취약의 가장 깊은 곳 = 고립
# ======================================================================
elif section == SECTIONS[6]:
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


    st.subheader("고립의 심도 — 공식 '은둔' 지표와 외부 수렴")
    st.markdown("파생 고립지표를 넘어, **공식 '은둔 지속기간' 변수**로 보면 은둔이 길수록 삶 만족이 "
                "**단조 하락**(용량반응)하고, 정부 공식조사와 **수치가 수렴**한다.")

    show_fig("23_rested_seclusion_doseresponse.png",
             "좌: 은둔 기간↑ → 삶만족↓ (6.70→3.75). 우: 복지부 2023 고립·은둔 조사(3.7 vs 6.7)와 수렴.")
    method_note(
        """
**변수** · 청년삶 2024 공식 `seclusion_duration`(은둔 지속기간). 가중 평균 삶만족 + Spearman 추세.
**왜 강한가** · binary 고립(외출 7~8점, n=41)보다 **풍부**(은둔 경험자 n=226)하고 **단계적 하락**(용량반응)이 보인다.
**외부 수렴** · 복지부 2023 고립·은둔 청년 실태조사(삶만족 3.7 vs 전체청년 6.7)와 우리 양끝(6.70·3.75)이 거의 일치
→ 미시결과가 **외부 조사와 같은 방향**인지 확인하는 데 쓴다(소표본 한계 보완).
**한계** · 장기은둔군 소표본(n≤20), 2024 단년(2022엔 변수 부재 → 연도비교 불가).
"""
    )


# ======================================================================
# S7 ★전국 일반화 (KGSS) — KOSSDA 기둥★
# ======================================================================
elif section == SECTIONS[7]:
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
# S8 재현성·추세 (2022 ↔ 2024)
# ======================================================================
elif section == SECTIONS[8]:
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
# S9 결론
# ======================================================================
else:
    st.header("결론 · 정책 함의")
    no_help = queries.weighted_share(rested, "no_help_flag")
    risk_pct = float((pd.to_numeric(rested.get("risk_score"), errors="coerce") >= 2).mean() * 100)
    st.markdown(
        f"""
### 핵심 요약
- **쉬었음 ≠ 실업자**: 별개의 비경제활동 집단으로 다뤄야 한다(S1).
- **쉬었음 청년은 단일 집단이 아니다** — 가족·공공·금융 중 **무엇에 기대는가에 따라 분화**된다.
  다수는 가족으로 버티지만(가족 편중), 그 평균이 내부 격차를 가린다(S2).
- **가족 자원의 유무 = 경제적 위험의 격차**: 부모 비동거 청년의 부채 보유율은 동거의 약 2배(H1),
  가족지원 유무는 생활비 수준과도 유의하게 연관(H2)(S3).
- **공공은 가족의 공백을 메우지 못한다(H3)**: 가족지원이 없는 청년의 절반 이상이
  어디에도 도움을 청할 곳이 없고, 공공기관 도달률은 한 자릿수~10%대(S4).
- **위험은 소수에 중첩된다(H4)**: 위험요인 2개 이상 중첩 위험군 {risk_pct:.1f}%.
  유형 분화의 끝, **고립위험형은 자원도 웰빙도 최저**(S5).
- **격차의 가장 깊은 곳 = '고립'** — 고립 청년은 삶 만족 급락(r≈-0.47),
  도움없음 약 5.8배(Fisher). 공식 '은둔 기간'도 길수록 삶만족 단조 하락(외부조사와 수렴)(S6).
  - (`도움없음` 약 {no_help['모집단추정(명)']/10000:.1f}만 명, {no_help['비율_가중(%)']}%)
- **전국(KGSS) 재현**: 취업 여부보다 **고립**이 행복을 약 14배 더 가른다(취업·미취업 무관)(S7).
- **2022→2024**: 쉬었음 규모↑ + 내부 취약↑ + 가족 버팀목↓(평균은 그대로 = 내부격차 심화)(S8).

### 정책 함의
- **유형별 차등 접근**: 금융부담형엔 채무·생활비 지원, 고립위험형엔 관계망 회복·공공기관 연결 —
  단일 처방 대신 제한된 정책 자원의 정밀 배분.
- 가족지원을 암묵적 전제로 둔 청년정책은 **가족 자원이 끊긴 청년을 사각지대에 남긴다**
  → 가족지원 가용성 자체를 선별 기준의 하나로.
- 공공 안전망의 **도달 범위(coverage) 확대와 적극적 발굴·연계**가 시급하다.
- 사각지대의 최심부(고립·도움없음)는 소득지원보다 **사회적 연결·접촉 기반 개입**(관계망 재건)이 핵심.

### 선행연구와의 차별점
- 2025 수상작('캥거루 청년')은 *거주 독립·심리자본*. 본 연구는 ① 대상 **'쉬었음'(노동시장 밖)**,
  ② **생활안전망 격차로 내부를 유형화**하고, ③ 그 끝의 **사회적 고립(관계)** 을
  ④ **KGSS 전국 일반화**로 검증한 점에서 구별된다.
"""
    )
    st.caption("※ 한계: 소표본 하위집단(고립·도움없음)은 효과크기로 보고·경향 해석. 데이터 간 개인결합 불가(층위별 근거 결합). "
               "관찰연구라 인과 아님. KGSS는 전국 성인 일반화까지만 주장.")

st.divider()
st.caption("표시 수치는 청년삶 2024·2022·EAPS·KGSS·KLIPS 실데이터에서 계산. © 2026 경영정보처리론 · KOSSDA 공모전")
