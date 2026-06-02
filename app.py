"""청년 '쉬었음' 집단의 내부 취약성 분석 - Streamlit 앱.

메인 데이터: 청년삶실태조사 2024 (data/db/youth_analysis.sqlite3)
표시되는 모든 수치는 적재된 실제 데이터에서 계산된 값이다 (임의 생성 없음).

파이프라인:
    data/raw → preprocess.py → data/processed → build_db.py → SQLite → app.py
실행:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import queries
from src.charts import bar_chart, box_chart, grouped_bar, histogram

st.set_page_config(
    page_title="청년 쉬었음 집단의 내부 취약성 분석",
    page_icon="📊",
    layout="wide",
)

DB_PATH = queries.DB_PATH
RESTED = queries.YOUTH_RESTED_TABLE
ALL = queries.YOUTH_ALL_TABLE

# 분석에 쓰는 컬럼 → 화면 표시용 한글 라벨
LABELS = {
    "living_cost": "월평균 총생활비",
    "income_year": "청년 연간소득",
    "transfer_private": "사적 이전소득",
    "transfer_public": "공적 이전소득",
    "debt_total": "청년 부채 총액",
    "debt_living": "생활비 부채",
    "interest_monthly": "월평균 이자",
    "debt_student": "학자금 부채",
    "debt_housing": "주택관련 부채",
    "subjective_class": "주관적 계층 인식(1하층~5상층)",
    "life_satisfaction": "삶 만족도(0~10)",
    "happiness": "행복감(0~10)",
}
ECON_VARS = [
    "living_cost", "income_year", "transfer_private", "transfer_public",
    "debt_total", "debt_living", "interest_monthly",
]
COMPARE_VARS = [
    "living_cost", "income_year", "debt_total", "interest_monthly",
    "subjective_class", "life_satisfaction",
]


# ----------------------------------------------------------------------
# 데이터 접근 (DB/테이블 없어도 죽지 않도록 캐시 + 가드)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_tables() -> list[str]:
    return queries.list_tables()


@st.cache_data(show_spinner=False)
def numeric_summary(table: str, cols: tuple[str, ...]) -> pd.DataFrame:
    return queries.numeric_summary(table, list(cols))


@st.cache_data(show_spinner=False)
def help_share(table: str) -> pd.DataFrame:
    return queries.help_network_share(table)


@st.cache_data(show_spinner=False)
def group_means(table: str, group_col: str, value_cols: tuple[str, ...]) -> pd.DataFrame:
    return queries.group_means(table, group_col, list(value_cols))


@st.cache_data(show_spinner=False)
def labor_group_counts(table: str) -> pd.DataFrame:
    sql = (
        f'SELECT labor_group AS 노동상태, COUNT(*) AS 인원 '
        f'FROM "{table}" GROUP BY labor_group ORDER BY 인원 DESC;'
    )
    return queries.run_query(sql)


@st.cache_data(show_spinner=False)
def fetch_series(table: str, col: str) -> pd.Series:
    df = queries.run_query(f'SELECT "{col}" FROM "{table}";')
    return pd.to_numeric(df[col], errors="coerce").dropna()


def lab(col: str) -> str:
    return LABELS.get(col, col)


# ----------------------------------------------------------------------
# 헤더 & 데이터 가용성 확인
# ----------------------------------------------------------------------
st.title("청년 쉬었음 집단의 내부 취약성 분석")
st.caption("KOSSDA 대학생 데이터 시각화 공모전 / 경영정보처리론 · 메인 데이터: 청년삶실태조사 2024")

tables = get_tables() if queries.db_exists(DB_PATH) else []
ready = RESTED in tables and ALL in tables

if not ready:
    st.warning(
        "분석용 DB/테이블이 아직 없습니다. 아래 순서로 파이프라인을 실행하세요.",
        icon="📂",
    )
    st.code(
        "1) data/raw/youth_life/ 에 청년삶 2024 원본 넣기\n"
        "2) python src/preprocess.py     # 쉬었음 표본 생성\n"
        "3) python src/build_db.py       # SQLite 적재\n"
        "4) streamlit run app.py         # 새로고침",
        language="text",
    )
    st.stop()

# ----------------------------------------------------------------------
# 사이드바 네비게이션
# ----------------------------------------------------------------------
SECTIONS = [
    "0. 개요 · 문제의식",
    "1. 쉬었음 정의 & 표본",
    "2. 분석1 · 쉬었음 청년 기술통계",
    "3. 분석2 · 생활비 지원망",
    "4. 분석3 · 부모동거 vs 비동거",
    "5. 분석4 · 도움 있음 vs 없음",
    "6. 데이터 탐색(부록)",
]
section = st.sidebar.radio("화면 이동", SECTIONS)
st.sidebar.caption("모든 수치는 청년삶 2024 실데이터에서 계산됩니다.")

# ======================================================================
# 0. 개요
# ======================================================================
if section == SECTIONS[0]:
    st.header("프로젝트 개요 · 문제의식")
    st.markdown(
        """
청년 노동시장 문제는 **실업률만으로 설명되지 않는다.** 구직활동을 하지 않아 비경제활동으로
분류되는 **'쉬었음'** 청년이 정책 사각지대에 놓이기 때문이다.

이 프로젝트는 쉬었음 청년을 **단일 집단이 아니라 내부 구조를 가진 집단**으로 보고,
경제·금융·생활안전망·인식 조건에 따른 **내부 취약성 차이**를 분석한다.

> 핵심 질문: *"쉬었음 청년은 무엇으로 버티는가? 그리고 누가 더 취약한가?"*
"""
    )
    st.info(
        "메인 데이터: **청년삶실태조사 2024** (전체 15,098명). "
        "KLIPS(보조 검증), 경제활동인구조사(배경)는 이후 단계에서 추가됩니다.",
        icon="🗂️",
    )

# ======================================================================
# 1. 쉬었음 정의 & 표본
# ======================================================================
elif section == SECTIONS[1]:
    st.header("쉬었음 정의 & 표본")
    st.markdown(
        """
**쉬었음 필터 (코드북 기준 확정)**

```
경제활동상태 = 8 (비경제활동인구)
AND 지난 주 주된 활동 상태 = 10 (쉬었음)
```
육아·가사·통학·취업준비·요양 등과 구분되는 **순수 '쉬었음'** 만 추출했습니다.
"""
    )
    counts = labor_group_counts(ALL)
    total = int(counts["인원"].sum())
    rested_n = int(counts.loc[counts["노동상태"] == "비경활_쉬었음", "인원"].sum())

    c1, c2 = st.columns(2)
    c1.metric("전체 응답자", f"{total:,}명")
    c2.metric("쉬었음 청년 표본", f"{rested_n:,}명", f"{rested_n/total*100:.1f}%")

    fig = bar_chart(counts, x="노동상태", y="인원", title="청년 노동상태 구성 (청년삶 2024)")
    st.plotly_chart(fig, width="stretch")
    st.caption("실제 데이터 기반 집계입니다.")

# ======================================================================
# 2. 분석1 · 기술통계
# ======================================================================
elif section == SECTIONS[2]:
    st.header("분석1 · 쉬었음 청년 기술통계")
    st.markdown(
        "쉬었음 청년의 경제 조건은 **평균 하나로 설명되지 않는다.** "
        "0 비율과 양수자 평균을 함께 보면 분포의 쏠림이 드러납니다."
    )
    summ = numeric_summary(RESTED, tuple(ECON_VARS)).copy()
    summ["변수"] = summ["변수"].map(lab)
    st.dataframe(summ, width="stretch", hide_index=True)
    st.caption("단위는 코드북(파일설계서) 정의를 따릅니다. 모든 값은 쉬었음 1,062명에서 계산.")

    st.subheader("변수 분포 보기")
    pick = st.selectbox("변수 선택", options=ECON_VARS, format_func=lab)
    s = fetch_series(RESTED, pick)
    fig = histogram(pd.DataFrame({lab(pick): s.values}), x=lab(pick),
                    title=f"{lab(pick)} 분포 (쉬었음 청년, n={s.size:,})", nbins=30)
    st.plotly_chart(fig, width="stretch")

# ======================================================================
# 3. 분석2 · 생활비 지원망
# ======================================================================
elif section == SECTIONS[3]:
    st.header("분석2 · 생활비 지원망")
    st.markdown(
        "쉬었음 청년은 **이번 달 생활비가 부족할 때 누구의 도움**을 받을 수 있다고 응답했는가? "
        "(복수응답, %)"
    )
    share = help_share(RESTED)
    fig = bar_chart(share, x="집단", y="비율(%)", title="생활비 부족 시 도움 가능 집단 (쉬었음 청년)")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(share, width="stretch", hide_index=True)

    no_help_pct = float(share.loc[share["집단"] == "없음", "비율(%)"].iloc[0])
    st.metric("생활안전망 '없음' 응답", f"{no_help_pct:.1f}%",
              help="도움 받을 집단이 없다고 응답한 비율 = 취약 후보 집단")

# ======================================================================
# 4. 분석3 · 부모동거 vs 비동거
# ======================================================================
elif section == SECTIONS[4]:
    st.header("분석3 · 부모동거 vs 비동거")
    st.markdown("가족 완충(부모 동거)이 경제·인식 조건 차이로 이어지는지 비교합니다.")
    gm = group_means(RESTED, "parents_label", tuple(COMPARE_VARS))
    gm = gm.rename(columns={c: lab(c) for c in COMPARE_VARS})
    st.dataframe(gm, width="stretch", hide_index=True)

    pick = st.selectbox("비교할 변수", options=COMPARE_VARS, format_func=lab)
    gm2 = group_means(RESTED, "parents_label", (pick,))
    fig = bar_chart(gm2, x="parents_label", y=pick,
                    title=f"부모동거 여부별 {lab(pick)} 평균 (쉬었음 청년)")
    fig.update_layout(xaxis_title="", yaxis_title=lab(pick))
    st.plotly_chart(fig, width="stretch")

# ======================================================================
# 5. 분석4 · 도움 있음 vs 없음
# ======================================================================
elif section == SECTIONS[5]:
    st.header("분석4 · 생활안전망 있음 vs 없음")
    st.markdown("생활비 도움망이 **없는** 집단이 실제로 더 취약한지 비교합니다.")
    gm = group_means(RESTED, "no_help", tuple(COMPARE_VARS)).copy()
    gm["그룹"] = gm["no_help"].map({0: "도움망 있음", 1: "도움망 없음"})
    gm_show = gm[["그룹"] + COMPARE_VARS].rename(columns={c: lab(c) for c in COMPARE_VARS})
    st.dataframe(gm_show, width="stretch", hide_index=True)

    pick = st.selectbox("비교할 변수", options=COMPARE_VARS, format_func=lab)
    plot_df = gm[["그룹", pick]]
    fig = bar_chart(plot_df, x="그룹", y=pick,
                    title=f"생활안전망 유무별 {lab(pick)} 평균 (쉬었음 청년)")
    fig.update_layout(xaxis_title="", yaxis_title=lab(pick))
    st.plotly_chart(fig, width="stretch")

# ======================================================================
# 6. 데이터 탐색(부록)
# ======================================================================
else:
    st.header("데이터 탐색 (부록)")
    table = st.selectbox("테이블 선택", options=tables)
    cols = queries.list_columns(table)
    st.write(f"**{table}** · {len(cols)}개 컬럼")
    st.dataframe(queries.preview_table(table, limit=20), width="stretch")

    pick = st.selectbox("값 빈도(value_counts)를 볼 컬럼", options=cols)
    vc = queries.run_query(
        f'SELECT "{pick}" AS 값, COUNT(*) AS 빈도 FROM "{table}" '
        f'GROUP BY "{pick}" ORDER BY 빈도 DESC LIMIT 20;'
    )
    vc["값"] = vc["값"].astype(str)
    st.plotly_chart(
        bar_chart(vc, x="값", y="빈도", title=f"'{pick}' 값 빈도 (상위 20)"),
        width="stretch",
    )

st.divider()
st.caption(
    "표시 수치는 청년삶 2024 실데이터에서 계산되며 임의로 생성하지 않습니다. "
    "© 2026 경영정보처리론 · KOSSDA 대학생 공모전 프로젝트"
)
