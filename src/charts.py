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


if __name__ == "__main__":
    # 샘플 데이터로 동작 확인용 (실제 분석 결과 아님)
    sample = pd.DataFrame(
        {"category": ["A", "B", "C"], "value": [10, 20, 15]}
    )
    fig = bar_chart(sample, x="category", y="value", title="샘플 막대그래프")
    print("charts.bar_chart 생성 완료:", type(fig))
    fig2 = histogram(sample, x="value", title="샘플 히스토그램")
    print("charts.histogram 생성 완료:", type(fig2))
