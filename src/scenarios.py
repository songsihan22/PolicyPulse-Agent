"""Scenario and intervention definitions for the simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """A public governance policy scenario."""

    name: str
    description: str
    policy_valence: float
    risk_level: float
    benefit_level: float
    trust_relevance: float


SCENARIOS: dict[str, Scenario] = {
    "生成式 AI 进入高校课堂": Scenario(
        name="生成式 AI 进入高校课堂",
        description=(
            "该场景聚焦高校是否将生成式 AI 工具系统性引入课堂、作业辅导与教学评价，"
            "公众讨论通常围绕教学效率、学术诚信、教育公平与教师角色变化展开。"
        ),
        policy_valence=0.30,
        risk_level=0.45,
        benefit_level=0.72,
        trust_relevance=0.52,
    ),
    "生成式 AI 内容监管": Scenario(
        name="生成式 AI 内容监管",
        description=(
            "该场景聚焦平台、监管机构与公众如何看待生成式 AI 内容标识、审核责任与言论边界，"
            "讨论通常涉及创新激励、风险控制与表达自由之间的平衡。"
        ),
        policy_valence=-0.05,
        risk_level=0.72,
        benefit_level=0.42,
        trust_relevance=0.60,
    ),
    "城市公共摄像头治理": Scenario(
        name="城市公共摄像头治理",
        description=(
            "该场景聚焦城市公共摄像头在安全治理中的部署、边界与监督机制，"
            "涉及治安收益、隐私保护、程序正义与制度约束等议题。"
        ),
        policy_valence=0.05,
        risk_level=0.68,
        benefit_level=0.58,
        trust_relevance=0.74,
    ),
    "金融 AI 风控透明度": Scenario(
        name="金融 AI 风控透明度",
        description=(
            "该场景聚焦金融机构使用 AI 进行授信、反欺诈与风险控制时，是否需要提高解释性与透明度，"
            "公众关注效率、公平、歧视风险与申诉机制。"
        ),
        policy_valence=0.18,
        risk_level=0.63,
        benefit_level=0.61,
        trust_relevance=0.66,
    ),
    "公共数据开放治理": Scenario(
        name="公共数据开放治理",
        description=(
            "该场景聚焦政府开放公共数据以促进创新与服务协同的同时，如何回应隐私、数据安全、"
            "授权边界与社会监督问题。"
        ),
        policy_valence=0.22,
        risk_level=0.57,
        benefit_level=0.69,
        trust_relevance=0.64,
    ),
}


INTERVENTIONS: dict[str, dict[str, float]] = {
    "官方政策解释": {
        "trust_shift": 0.22,
        "risk_shift": -0.08,
        "benefit_shift": 0.08,
        "social_temperature": 0.02,
    },
    "专家理性说明": {
        "trust_shift": 0.12,
        "risk_shift": -0.03,
        "benefit_shift": 0.05,
        "social_temperature": 0.01,
    },
    "负面新闻冲击": {
        "trust_shift": -0.16,
        "risk_shift": 0.18,
        "benefit_shift": -0.10,
        "social_temperature": 0.06,
    },
    "社交媒体情绪传播": {
        "trust_shift": -0.04,
        "risk_shift": 0.05,
        "benefit_shift": 0.00,
        "social_temperature": 0.12,
    },
    "平衡型公共讨论": {
        "trust_shift": 0.06,
        "risk_shift": -0.01,
        "benefit_shift": 0.02,
        "social_temperature": 0.03,
    },
}


PERSONA_TEMPLATES: dict[str, dict[str, float]] = {
    "技术乐观型": {
        "attitude": 0.45,
        "institutional_trust": 0.52,
        "risk_sensitivity": 0.28,
        "benefit_sensitivity": 0.82,
        "conformity": 0.42,
        "openness": 0.78,
        "expression_strength": 0.72,
    },
    "风险敏感型": {
        "attitude": -0.28,
        "institutional_trust": 0.40,
        "risk_sensitivity": 0.88,
        "benefit_sensitivity": 0.34,
        "conformity": 0.38,
        "openness": 0.45,
        "expression_strength": 0.62,
    },
    "制度信任型": {
        "attitude": 0.10,
        "institutional_trust": 0.84,
        "risk_sensitivity": 0.44,
        "benefit_sensitivity": 0.58,
        "conformity": 0.60,
        "openness": 0.50,
        "expression_strength": 0.48,
    },
    "权益保护型": {
        "attitude": -0.18,
        "institutional_trust": 0.38,
        "risk_sensitivity": 0.80,
        "benefit_sensitivity": 0.40,
        "conformity": 0.34,
        "openness": 0.57,
        "expression_strength": 0.74,
    },
    "功利效率型": {
        "attitude": 0.22,
        "institutional_trust": 0.56,
        "risk_sensitivity": 0.36,
        "benefit_sensitivity": 0.76,
        "conformity": 0.46,
        "openness": 0.61,
        "expression_strength": 0.58,
    },
    "中立观望型": {
        "attitude": 0.00,
        "institutional_trust": 0.48,
        "risk_sensitivity": 0.50,
        "benefit_sensitivity": 0.50,
        "conformity": 0.55,
        "openness": 0.42,
        "expression_strength": 0.36,
    },
}


def get_scenario_options() -> dict[str, Scenario]:
    """Return the built-in scenarios."""
    return SCENARIOS


def get_scenario(name: str) -> Scenario:
    """Fetch a single scenario by name."""
    return SCENARIOS[name]


def get_intervention(name: str) -> dict[str, float]:
    """Fetch a single intervention profile by name."""
    return INTERVENTIONS[name]


def get_persona_templates() -> dict[str, dict[str, float]]:
    """Return built-in persona templates."""
    return PERSONA_TEMPLATES

