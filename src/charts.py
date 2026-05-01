"""Plotly chart builders for the simulation results."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def plot_average_attitude(df: pd.DataFrame):
    """Plot mean attitude by round."""
    chart_df = df.groupby("round", as_index=False)["attitude"].mean()
    fig = px.line(
        chart_df,
        x="round",
        y="attitude",
        markers=True,
        title="群体平均态度演化趋势",
        labels={"round": "轮次", "attitude": "平均态度"},
    )
    fig.update_layout(yaxis_range=[-1, 1], template="plotly_white")
    return fig


def plot_group_distribution(df: pd.DataFrame):
    """Plot support/neutral/oppose ratio by round."""
    chart_df = (
        df.groupby(["round", "stance"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    totals = chart_df.groupby("round")["count"].transform("sum")
    chart_df["ratio"] = chart_df["count"] / totals
    fig = px.area(
        chart_df,
        x="round",
        y="ratio",
        color="stance",
        title="支持、中立与反对立场的比例变化",
        labels={"round": "轮次", "ratio": "比例", "stance": "态度分类"},
        category_orders={"stance": ["支持", "中立", "反对"]},
    )
    fig.update_layout(yaxis_tickformat=".0%", template="plotly_white")
    return fig


def plot_persona_attitude(df: pd.DataFrame):
    """Plot mean attitude by persona type over time."""
    chart_df = df.groupby(["round", "persona_type"], as_index=False)["attitude"].mean()
    fig = px.line(
        chart_df,
        x="round",
        y="attitude",
        color="persona_type",
        markers=True,
        title="不同 Agent 类型的平均态度演化",
        labels={"round": "轮次", "attitude": "平均态度", "persona_type": "Agent 类型"},
    )
    fig.update_layout(yaxis_range=[-1, 1], template="plotly_white", legend_title_text="Agent 类型")
    return fig
