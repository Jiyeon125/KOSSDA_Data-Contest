"""청년 '쉬었음' 집단의 내부 취약성 분석 - Streamlit 앱.

실데이터 최소 파이프라인 단계:
    1) data/raw 에 원본 데이터 넣기
    2) python src/inspect_data.py   (구조 확인)
    3) python src/preprocess.py     (전처리)
    4) python src/build_db.py       (SQLite 적재)
    5) streamlit run app.py         (확인)

주의:
    DB 파일이 없어도 앱은 죽지 않고 안내 메시지를 보여준다.
    실제 분석 결과를 임의로 만들지 않으며, DB 에서 계산된 값만 표시한다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src import queries
from src.charts import bar_chart, histogram

# ----------------------------------------------------------------------
# 페이지 기본 설정
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="청년 쉬었음 집단의 내부 취약성 분석",
    page_icon="📊",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = queries.DB_PATH


# ----------------------------------------------------------------------
# 데이터 접근 헬퍼 (DB 가 없어도 앱이 죽지 않도록 캐시 + 예외 처리)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_tables() -> list[str]:
    return queries.list_tables()


@st.cache_data(show_spinner=False)
def get_columns(table_name: str) -> list[str]:
    return queries.list_columns(table_name)


@st.cache_data(show_spinner=False)
def get_preview(table_name: str, limit: int = 20) -> pd.DataFrame:
    return queries.preview_table(table_name, limit=limit)


@st.cache_data(show_spinner=False)
def get_value_counts(table_name: str, column: str, top_n: int = 20) -> pd.DataFrame:
    """선택한 컬럼의 value_counts 를 SQL 로 계산해 DataFrame 으로 반환한다."""
    safe_table = str(table_name).replace('"', '""')
    safe_col = str(column).replace('"', '""')
    sql = (
        f'SELECT "{safe_col}" AS 값, COUNT(*) AS 빈도 '
        f'FROM "{safe_table}" '
        f'GROUP BY "{safe_col}" '
        f'ORDER BY 빈도 DESC '
        f'LIMIT ?;'
    )
    return queries.run_query(sql, params=(top_n,))


@st.cache_data(show_spinner=False)
def get_column_series(table_name: str, column: str, max_rows: int = 50000) -> pd.DataFrame:
    """선택한 컬럼 값을 (최대 max_rows 까지) 조회한다.

    데이터가 커질 수 있으므로 LIMIT 으로 상한을 둔다.
    """
    safe_table = str(table_name).replace('"', '""')
    safe_col = str(column).replace('"', '""')
    sql = f'SELECT "{safe_col}" AS 값 FROM "{safe_table}" LIMIT ?;'
    return queries.run_query(sql, params=(max_rows,))


# ----------------------------------------------------------------------
# 헤더
# ----------------------------------------------------------------------
st.title("청년 쉬었음 집단의 내부 취약성 분석")
st.caption("KOSSDA 대학생 데이터 시각화 공모전 / 경영정보처리론 수업 프로젝트")

# ----------------------------------------------------------------------
# 1. 프로젝트 개요
# ----------------------------------------------------------------------
st.header("1. 프로젝트 개요")
st.markdown(
    """
노동시장에서 **'쉬었음'** 으로 분류되는 청년 집단을 **단일 집단이 아닌 내부 구조를 가진
이질적 집단**으로 보고, 하위 유형별 취약성 차이를 데이터로 분석하는 프로젝트입니다.

이 화면은 **실데이터 최소 파이프라인** 확인용입니다.
`data/raw` 에 원본을 넣고 전처리 → SQLite 적재를 거치면, 아래에서 테이블/컬럼을 선택해
구조를 확인하고 간단한 빈도 시각화를 볼 수 있습니다.
"""
)

st.divider()

# ----------------------------------------------------------------------
# 2. 데이터 로딩 상태
# ----------------------------------------------------------------------
st.header("2. 데이터 로딩 상태")

db_ready = queries.db_exists(DB_PATH)
tables: list[str] = []

if not db_ready:
    st.warning(
        "아직 분석용 DB 파일이 없습니다.\n\n"
        f"경로: `{DB_PATH}`\n\n"
        "아래 순서로 파이프라인을 먼저 실행하세요.",
        icon="📂",
    )
    st.code(
        "1) 원본 데이터를 data/raw/ 에 넣기\n"
        "2) python src/inspect_data.py   # 데이터 구조 확인\n"
        "3) python src/preprocess.py     # 전처리\n"
        "4) python src/build_db.py       # SQLite DB 생성\n"
        "5) streamlit run app.py         # (현재 화면) 새로고침",
        language="text",
    )
else:
    try:
        tables = get_tables()
    except Exception as exc:  # noqa: BLE001
        st.error(f"DB 조회 중 오류가 발생했습니다: {exc}")
        tables = []

    if tables:
        st.success(f"DB 연결 성공: `{DB_PATH.name}` · 테이블 {len(tables)}개 발견", icon="✅")
    else:
        st.info(
            "DB 파일은 있으나 테이블이 없습니다. "
            "`python src/build_db.py` 로 데이터를 적재했는지 확인하세요.",
            icon="ℹ️",
        )

st.divider()

# ----------------------------------------------------------------------
# 3. DB 테이블 목록
# ----------------------------------------------------------------------
st.header("3. DB 테이블 목록")

if not tables:
    st.caption("표시할 테이블이 없습니다. (DB 생성 후 다시 확인하세요.)")
else:
    st.dataframe(
        pd.DataFrame({"테이블명": tables}),
        use_container_width=True,
        hide_index=True,
    )

# 테이블 선택 (사이드바)
selected_table: str | None = None
if tables:
    selected_table = st.sidebar.selectbox("테이블 선택", options=tables)

st.divider()

# ----------------------------------------------------------------------
# 4. 선택한 테이블 미리보기
# ----------------------------------------------------------------------
st.header("4. 선택한 테이블 미리보기")

if not selected_table:
    st.caption("테이블이 준비되면 사이드바에서 선택할 수 있습니다.")
else:
    try:
        preview_df = get_preview(selected_table, limit=20)
        st.write(f"**`{selected_table}`** 상위 {len(preview_df)}행")
        st.dataframe(preview_df, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"미리보기 조회 실패: {exc}")

st.divider()

# ----------------------------------------------------------------------
# 5. 선택한 테이블의 컬럼 정보
# ----------------------------------------------------------------------
st.header("5. 선택한 테이블의 컬럼 정보")

columns: list[str] = []
if not selected_table:
    st.caption("테이블을 선택하면 컬럼 정보가 표시됩니다.")
else:
    try:
        columns = get_columns(selected_table)
        st.write(f"**`{selected_table}`** 의 컬럼 {len(columns)}개")
        st.dataframe(
            pd.DataFrame({"컬럼명": columns}),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"컬럼 조회 실패: {exc}")

st.divider()

# ----------------------------------------------------------------------
# 6. 탐색 시각화 (1) - 값 빈도 막대그래프
# ----------------------------------------------------------------------
st.header("6. 탐색 시각화 (1) · 값 빈도")
st.markdown(
    "분석용 컬럼이 아직 확정되지 않았으므로, 선택한 컬럼의 "
    "**값 빈도(value_counts)** 를 막대그래프로 보여줍니다. "
    "*(모든 수치는 적재된 실데이터에서 계산된 값입니다.)*"
)

if not selected_table or not columns:
    st.caption("테이블과 컬럼이 준비되면 빈도 그래프를 그릴 수 있습니다.")
else:
    selected_column = st.selectbox("시각화할 컬럼 선택", options=columns)
    top_n = st.slider("상위 N개 값", min_value=5, max_value=30, value=15, step=1)

    try:
        counts_df = get_value_counts(selected_table, selected_column, top_n=top_n)
        if counts_df.empty:
            st.info("해당 컬럼에 표시할 값이 없습니다.")
        else:
            # 값 컬럼을 문자열로 바꿔 축이 깔끔하게 표시되도록 처리
            counts_df = counts_df.copy()
            counts_df["값"] = counts_df["값"].astype(str)

            fig = bar_chart(
                counts_df,
                x="값",
                y="빈도",
                title=f"'{selected_column}' 값 빈도 (상위 {top_n})",
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("빈도 표 보기"):
                st.dataframe(counts_df, use_container_width=True, hide_index=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"빈도 계산 실패: {exc}")

st.divider()

# ----------------------------------------------------------------------
# 7. 탐색 시각화 (2) - 수치형 컬럼 히스토그램
# ----------------------------------------------------------------------
st.header("7. 탐색 시각화 (2) · 수치형 분포")
st.markdown(
    "선택한 컬럼이 **수치형**일 경우 히스토그램으로 분포를 확인합니다. "
    "*(코드값일 수 있으므로 분포 해석은 코드북 확인 후 진행하세요.)*"
)

if not selected_table or not columns:
    st.caption("테이블과 컬럼이 준비되면 히스토그램을 그릴 수 있습니다.")
else:
    hist_column = st.selectbox(
        "히스토그램을 볼 컬럼 선택", options=columns, key="hist_col"
    )
    nbins = st.slider("구간(bin) 개수", min_value=5, max_value=60, value=30, step=1)

    try:
        series_df = get_column_series(selected_table, hist_column)
        # 문자열 등으로 저장된 값을 수치로 변환 시도 (변환 불가 값은 결측 처리)
        numeric_values = pd.to_numeric(series_df["값"], errors="coerce").dropna()

        if numeric_values.empty:
            st.info(
                "이 컬럼은 수치형으로 해석할 수 없어 히스토그램을 그릴 수 없습니다. "
                "(범주형 컬럼은 위의 '값 빈도' 섹션을 사용하세요.)"
            )
        else:
            plot_df = pd.DataFrame({hist_column: numeric_values.values})
            fig_hist = histogram(
                plot_df,
                x=hist_column,
                title=f"'{hist_column}' 분포 (수치형, n={len(numeric_values):,})",
                nbins=nbins,
            )
            st.plotly_chart(fig_hist, use_container_width=True)

            with st.expander("기초 통계 보기"):
                st.dataframe(
                    numeric_values.describe().to_frame(name=hist_column),
                    use_container_width=True,
                )
    except Exception as exc:  # noqa: BLE001
        st.error(f"히스토그램 생성 실패: {exc}")

st.divider()
st.caption(
    "본 화면은 실데이터 최소 파이프라인 확인용입니다. "
    "표시 수치는 적재된 데이터에서 계산되며 임의로 생성하지 않습니다. "
    "© 2026 경영정보처리론 · KOSSDA 대학생 공모전 프로젝트"
)
