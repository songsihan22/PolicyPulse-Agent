"""Streamlit entrypoint for PolicyPulse-Agent."""

from __future__ import annotations

import streamlit as st

from src.charts import (
    plot_average_attitude,
    plot_group_distribution,
    plot_persona_attitude,
)
from src.models import SimulationConfig
from src.report import (
    generate_governance_report,
    generate_representative_comments,
)
from src.scenarios import get_scenario_options
from src.simulator import run_simulation, summarize_final_distribution
from src.utils import get_reference_assets_summary


st.set_page_config(
    page_title="PolicyPulse-Agent",
    layout="wide",
)


def main() -> None:
    """Render the Streamlit application."""
    st.title("PolicyPulse-Agent：公共治理场景下的多智能体态度演化模拟系统")

    st.markdown(
        """
        本系统是一个面向 **AI×公共治理** 场景的计算社会科学原型，聚焦 **政策沟通**、
        **公众态度演化** 与多类型 Agent 互动机制，适合用于 AI 治理、公共管理、
        人文社科交叉研究与展示型项目呈现。
        """
    )

    scenario_options = get_scenario_options()

    with st.sidebar:
        st.header("模拟参数")
        scenario_name = st.selectbox("政策场景", options=list(scenario_options.keys()))
        agent_count = st.slider("Agent 数量", min_value=10, max_value=300, value=60, step=10)
        rounds = st.slider("模拟轮数", min_value=3, max_value=50, value=12, step=1)
        intervention = st.selectbox(
            "信息干预方式",
            options=[
                "官方政策解释",
                "专家理性说明",
                "负面新闻冲击",
                "社交媒体情绪传播",
                "平衡型公共讨论",
            ],
        )
        seed = st.number_input("随机种子", min_value=0, max_value=999999, value=42, step=1)
        run_button = st.button("运行模拟", type="primary", use_container_width=True)

    selected_scenario = scenario_options[scenario_name]
    st.subheader("当前场景说明")
    st.info(selected_scenario.description)

    st.subheader("项目简介")
    st.write(
        "系统通过可解释的规则模拟政策信息影响、社交互动影响与随机扰动，不用于预测真实社会，"
        "主要用于教学、展示与探索性分析。"
    )

    reference_assets = get_reference_assets_summary()
    with st.expander("参考语料概览（可选）", expanded=False):
        st.caption(
            "项目运行不依赖大体量语料文件。若本地存在小样本参考文件，可用于辅助展示语料来源与议题示例；"
            "当前模拟系统并不会直接把参考语料当作现实预测依据。"
        )
        st.markdown("**sample_reference.jsonl**")
        if reference_assets["sample"]["exists"]:
            st.write(f"问题数：{reference_assets['sample']['question_count']}")
            st.write(f"答案数：{reference_assets['sample']['answer_count']}")
            st.write(
                f"平均每题答案数：{reference_assets['sample']['avg_answers_per_question']}"
            )
            st.write("示例题目：")
            for title in reference_assets["sample"]["sample_titles"]:
                st.markdown(f"- {title}")
        else:
            st.write("未检测到示例参考文件。")

    if not run_button:
        st.caption("请在左侧选择参数后点击“运行模拟”。")
        return

    config = SimulationConfig(
        scenario_name=scenario_name,
        num_agents=agent_count,
        num_rounds=rounds,
        intervention=intervention,
        random_seed=int(seed),
    )

    df = run_simulation(config)
    representative_comments = generate_representative_comments(df, selected_scenario, intervention)
    governance_report = generate_governance_report(df, selected_scenario, intervention)
    final_round = df["round"].max()
    final_df = df.loc[df["round"] == final_round]
    final_distribution = summarize_final_distribution(df)
    final_average = final_df["attitude"].mean()
    total_agents = max(1, len(final_df))

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("最终平均态度", f"{final_average:.2f}")
    metric_col2.metric("最终支持率", f"{final_distribution['支持'] / total_agents:.1%}")
    metric_col3.metric("最终反对率", f"{final_distribution['反对'] / total_agents:.1%}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("群体平均态度演化趋势")
        st.plotly_chart(plot_average_attitude(df), use_container_width=True)
    with col2:
        st.subheader("群体立场结构变化")
        st.plotly_chart(plot_group_distribution(df), use_container_width=True)

    st.subheader("不同 Agent 类型的平均态度变化")
    st.plotly_chart(plot_persona_attitude(df), use_container_width=True)

    st.subheader("代表性 Agent 发言")
    for comment in representative_comments:
        st.markdown(f"- **{comment['persona_type']}（{comment['agent_id']}）**：{comment['comment']}")

    st.subheader("公共治理分析报告")
    st.markdown(governance_report)

    st.subheader("模拟结果表格预览")
    st.dataframe(df.head(200), use_container_width=True)


if __name__ == "__main__":
    main()
