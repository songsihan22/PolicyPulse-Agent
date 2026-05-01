"""Narrative outputs for comments and governance reports."""

from __future__ import annotations

import pandas as pd

from src.scenarios import Scenario
from src.simulator import summarize_final_distribution
from src.utils import attitude_to_label


PERSONA_COMMENT_TEMPLATES: dict[str, dict[str, str]] = {
    "技术乐观型": {
        "支持": "围绕“{scenario}”，我更看重技术创新、教学或治理流程优化带来的正向价值。结合“{intervention}”的信息环境，只要边界明确、工具使用规范，我倾向于支持把 AI 作为提升效率和能力扩展的辅助机制。",
        "中立": "对于“{scenario}”，我认可 AI 可能带来的创新红利，但仍希望看到更充分的试点反馈。当前在“{intervention}”的讨论下，我的态度偏谨慎支持，还需要观察具体落地效果。",
        "反对": "即使在“{intervention}”的背景下，我也担心“{scenario}”的推进节奏过快，可能让技术想象先行于治理准备。若缺少配套规范，创新价值未必能稳定转化为公共价值。",
    },
    "风险敏感型": {
        "支持": "就“{scenario}”而言，我并非否认 AI 的作用，而是希望风险识别先于大规模扩展。当前“{intervention}”缓和了一部分担忧，但隐私泄露、误用、作弊和风险外溢仍需持续监管。",
        "中立": "面对“{scenario}”，我最在意的是误用风险、监管不足和责任失配。“{intervention}”提供了一些解释，但要真正建立信任，还需要更细致的风控、审计和纠偏机制。",
        "反对": "在“{scenario}”问题上，我依然担心隐私、误用、作弊与监管滞后。如果“{intervention}”无法回应这些风险来源，我很难支持进一步放大应用范围。",
    },
    "制度信任型": {
        "支持": "对于“{scenario}”，只要规则清晰、程序透明、责任链条明确，我通常愿意给予制度推进一定空间。尤其在“{intervention}”下，官方解释和制度保障对我形成了较明显的正向影响。",
        "中立": "我对“{scenario}”的判断主要取决于制度设计是否充分。虽然“{intervention}”改善了信息透明度，但我仍希望看到更完整的程序说明、监督安排和执行细则。",
        "反对": "即便存在“{intervention}”，如果“{scenario}”缺少可执行的规则、透明的程序和清晰的问责机制，我也不会轻易转向支持。制度合法性仍是关键前提。",
    },
    "权益保护型": {
        "支持": "如果“{scenario}”能够同步强化知情权、申诉权和弱势群体保护，我并不排斥探索 AI 应用。“{intervention}”只有在回应公平与责任边界问题时，才可能提升我的接受度。",
        "中立": "围绕“{scenario}”，我更关注公平、知情权、责任边界以及弱势群体是否会承受额外负担。当前“{intervention}”有一定帮助，但还不足以完全化解这些权益顾虑。",
        "反对": "对于“{scenario}”，如果治理重心只放在效率而忽视公平、知情权和弱势群体保护，我会保持明确保留。即使有“{intervention}”，权益保障不到位也会削弱治理合法性。",
    },
    "功利效率型": {
        "支持": "从治理绩效和资源配置角度看，“{scenario}”若能降低成本、提升效率并改善管理便利性，我倾向于支持推进。“{intervention}”进一步增强了我对实际可操作性的判断。",
        "中立": "我会从投入产出、执行成本和治理绩效来评估“{scenario}”。在“{intervention}”的背景下，它看起来具备一定效率优势，但是否值得推广，还要看配套成本是否可控。",
        "反对": "如果“{scenario}”在现实中增加管理摩擦、推高合规成本或无法形成清晰绩效回报，那么即便有“{intervention}”，我也不会认为它是高质量治理方案。",
    },
    "中立观望型": {
        "支持": "就“{scenario}”而言，我目前可以理解支持方的依据，特别是在“{intervention}”之后，政策沟通比之前更清楚。不过我仍把这种支持视为阶段性的，需要继续看后续证据。",
        "中立": "对“{scenario}”我暂时保持观察态度。现阶段“{intervention}”提供了一些信息，但证据还不够完整，我希望看到更多案例、反馈和长期效果再作判断。",
        "反对": "即使近期“{intervention}”让讨论更充分，我对“{scenario}”仍觉得信息不足，现阶段不宜过快形成一致意见。继续观察和补充证据仍然很重要。",
    },
}


def generate_representative_comments(
    df: pd.DataFrame, scenario: Scenario, intervention: str
) -> list[dict[str, str]]:
    """Generate rule-based representative comments from the final round."""
    final_round = df["round"].max()
    final_df = df.loc[df["round"] == final_round].copy()
    comments: list[dict[str, str]] = []

    for persona_type, group in final_df.groupby("persona_type"):
        representative = group.iloc[(group["attitude"].abs()).argmax()]
        stance = attitude_to_label(float(representative["attitude"]))
        template = PERSONA_COMMENT_TEMPLATES[persona_type][stance]
        comment = template.format(scenario=scenario.name, intervention=intervention)
        comments.append(
            {
                "agent_id": str(representative["agent_id"]),
                "persona_type": persona_type,
                "comment": comment,
            }
        )

    return comments


def generate_governance_report(df: pd.DataFrame, scenario: Scenario, intervention: str) -> str:
    """Generate a formal governance analysis report."""
    initial_round = df["round"].min()
    final_round = df["round"].max()

    initial_mean = df.loc[df["round"] == initial_round, "attitude"].mean()
    final_mean = df.loc[df["round"] == final_round, "attitude"].mean()
    delta = final_mean - initial_mean

    final_distribution = summarize_final_distribution(df)
    persona_means = (
        df.loc[df["round"] == final_round]
        .groupby("persona_type")["attitude"]
        .mean()
        .sort_values(ascending=False)
    )
    highest_persona = persona_means.index[0]
    lowest_persona = persona_means.index[-1]
    polarization = float(persona_means.max() - persona_means.min())
    support_rate = final_distribution["支持"] / max(1, sum(final_distribution.values()))
    oppose_rate = final_distribution["反对"] / max(1, sum(final_distribution.values()))

    trend_text = "整体接受度有所提升" if delta > 0.05 else "整体态度略有回落" if delta < -0.05 else "整体态度总体平稳"
    polarization_text = (
        "不同群体之间出现了较明显分化"
        if polarization > 0.45
        else "不同群体之间虽有差异，但尚未形成强烈对立"
    )
    legitimacy_text = (
        "治理合法性基础相对较强，但仍需兼顾少数谨慎群体的风险顾虑。"
        if support_rate >= 0.5 and oppose_rate < 0.25
        else "公众接受度并未自动转化为稳固合法性，治理设计仍需回应不同群体的关切。"
    )

    return f"""
**一、总体判断**

本轮模拟围绕“{scenario.name}”展开，在“{intervention}”这一信息干预条件下，群体平均态度由 {initial_mean:.2f} 变化至 {final_mean:.2f}，说明 {trend_text}。从 AI 治理视角看，公众接受度并不是由单一政策信号决定，而是同时受到政策沟通质量、风险感知、制度信任、算法监管预期以及群体互动机制的共同影响。{legitimacy_text}

**二、群体结构特征**

在最终轮次中，支持者 {final_distribution["支持"]} 人，中立者 {final_distribution["中立"]} 人，反对者 {final_distribution["反对"]} 人。{polarization_text}。其中，平均态度相对更积极的群体是“{highest_persona}”，相对更谨慎或保留的群体是“{lowest_persona}”。这一结构说明，面对同一 AI 治理议题，不同公众并不会自然收敛为单一态度，而会围绕创新收益、风险外溢、权利保障和制度可信度形成差异化判断。尤其是在涉及算法应用、公共数据、课堂治理或监管透明度时，风险敏感型和权益保护型群体往往更关注程序正义与责任边界，而制度信任型群体更容易受到正式解释和规则明确性的影响。

**三、公共治理启示**

从公共管理与 AI 治理视角看，至少有四点启示。第一，政策沟通不能只强调技术先进性，还需要把应用边界、问责链条、纠错机制和算法监管安排讲清楚。第二，制度信任能够提升正式政策解释的效果，但这种效果通常建立在程序透明和执行可信的前提之上。第三，面对风险感知较高或权益保护诉求较强的公众，仅以效率和便利性作为论证并不足够，必须同步回应知情权、公平性、申诉权与弱势群体保护问题。第四，群体分化并不必然意味着治理失败，它也可能提示治理部门需要采用更精细的分层沟通策略，以增强政策接受度并巩固治理合法性。

**四、研究定位说明**

本系统是解释性、探索性的 AI×社会科学模拟原型，适合用于课堂展示、研究讨论与概念验证。它能够帮助观察公众态度演化的方向、节奏与分化结构，但不构成对真实社会行为或政策结果的预测。
""".strip()
