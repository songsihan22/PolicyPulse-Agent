from src.models import AgentProfile, SimulationConfig


def test_agent_profile_creation():
    agent = AgentProfile(
        agent_id="A001",
        persona_type="技术乐观型",
        attitude=0.5,
        institutional_trust=0.6,
        risk_sensitivity=0.3,
        benefit_sensitivity=0.8,
        conformity=0.4,
        openness=0.7,
        expression_strength=0.6,
    )

    assert agent.agent_id == "A001"
    assert agent.attitude == 0.5


def test_simulation_config_creation():
    config = SimulationConfig(
        scenario_name="生成式 AI 进入高校课堂",
        num_agents=60,
        num_rounds=12,
        intervention="官方政策解释",
        random_seed=42,
    )

    assert config.num_agents == 60
    assert config.num_rounds == 12

