"""Plotly 기반 차트 함수 모음.

app.py 등에서 재사용할 수 있도록 시각화 로직을 분리한다.
실제 데이터가 준비되면 함수를 추가/확장하면 된다.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "막대그래프",
    color: str | None = None,
) -> go.Figure:
    """기본 막대그래프를 생성한다.

    Args:
        df: 시각화할 DataFrame.
        x: x축으로 사용할 컬럼명.
        y: y축으로 사용할 컬럼명.
        title: 차트 제목.
        color: 색상 구분에 사용할 컬럼명 (선택).

    Returns:
        plotly Figure 객체.
    """
    fig = px.bar(df, x=x, y=y, color=color, title=title, text_auto=True)
    fig.update_layout(
        xaxis_title=x,
        yaxis_title=y,
        title_x=0.0,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def histogram(
    df: pd.DataFrame,
    x: str,
    title: str = "히스토그램",
    nbins: int = 30,
) -> go.Figure:
    """수치형 컬럼의 분포를 보는 히스토그램을 생성한다.

    Args:
        df: 시각화할 DataFrame.
        x: 분포를 볼 (수치형) 컬럼명.
        title: 차트 제목.
        nbins: 구간(bin) 개수.

    Returns:
        plotly Figure 객체.
    """
    fig = px.histogram(df, x=x, nbins=nbins, title=title)
    fig.update_layout(
        xaxis_title=x,
        yaxis_title="빈도",
        title_x=0.0,
        bargap=0.05,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def grouped_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: str = "그룹 막대그래프",
    barmode: str = "group",
    color_map: dict | None = None,
    category_orders: dict | None = None,
    x_title: str | None = None,
    y_title: str | None = None,
    text_format: str = "auto",
) -> go.Figure:
    """그룹(색상)별 막대그래프를 생성한다 (집단 비교용).

    Args:
        df: long 형태의 DataFrame.
        x: x축 범주 컬럼.
        y: y축 값 컬럼.
        color: 그룹(색상) 구분 컬럼.
        title: 차트 제목.
        barmode: "group" | "stack".
        color_map: {그룹값: 색상} 매핑(선택).
        category_orders: {컬럼: [순서]} 정렬(선택).
        text_format: "auto" | plotly d3 포맷(예 ".1f").
    """
    fig = px.bar(
        df, x=x, y=y, color=color, barmode=barmode, title=title,
        text_auto=text_format,
        color_discrete_map=color_map,
        category_orders=category_orders,
    )
    fig.update_layout(
        title_x=0.0,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text=color,
        xaxis_title=x_title if x_title is not None else x,
        yaxis_title=y_title if y_title is not None else y,
    )
    return fig


def line_dual_axis(
    df: pd.DataFrame,
    x: str,
    y_left: str,
    y_right: str,
    name_left: str,
    name_right: str,
    title: str = "추이",
    left_title: str = "",
    right_title: str = "",
) -> go.Figure:
    """이중 y축 라인 차트 (예: 좌=실업률%, 우=쉬었음 천명)."""
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df[x], y=df[y_left], name=name_left, mode="lines+markers",
                   line=dict(color="#F58518")),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df[x], y=df[y_right], name=name_right, mode="lines+markers",
                   line=dict(color="#E45756")),
        secondary_y=True,
    )
    fig.update_layout(
        title=title, title_x=0.0, margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(title_text=x)
    # 0 기준선부터 그려 축 왜곡(과장)으로 보이지 않게 한다
    fig.update_yaxes(title_text=left_title, secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title_text=right_title, secondary_y=True, rangemode="tozero")
    return fig


def donut(
    labels: list[str],
    values: list[float],
    title: str = "구성비",
    color_map: dict | None = None,
) -> go.Figure:
    """도넛 차트 (구성비)."""
    colors = [color_map.get(l) for l in labels] if color_map else None
    fig = go.Figure(
        go.Pie(labels=labels, values=values, hole=0.5,
               marker=dict(colors=colors), sort=False,
               textinfo="label+percent")
    )
    fig.update_layout(title=title, title_x=0.0, margin=dict(l=20, r=20, t=60, b=20))
    return fig


def box_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "박스플롯",
) -> go.Figure:
    """그룹(x)별 수치 분포 박스플롯을 생성한다.

    Args:
        df: 시각화할 DataFrame.
        x: 그룹 컬럼.
        y: 수치 컬럼.
        title: 차트 제목.
    """
    fig = px.box(df, x=x, y=y, title=title, points="outliers")
    fig.update_layout(
        title_x=0.0,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


if __name__ == "__main__":
    # 샘플 데이터로 동작 확인용 (실제 분석 결과 아님)
    sample = pd.DataFrame(
        {"category": ["A", "B", "C"], "value": [10, 20, 15]}
    )
    fig = bar_chart(sample, x="category", y="value", title="샘플 막대그래프")
    print("charts.bar_chart 생성 완료:", type(fig))
    fig2 = histogram(sample, x="value", title="샘플 히스토그램")
    print("charts.histogram 생성 완료:", type(fig2))
