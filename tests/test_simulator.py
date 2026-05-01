from src.models import SimulationConfig
from src.simulator import run_simulation


def test_run_simulation_returns_non_empty_dataframe():
    config = SimulationConfig(
        scenario_name="生成式 AI 进入高校课堂",
        num_agents=30,
        num_rounds=6,
        intervention="平衡型公共讨论",
        random_seed=7,
    )

    df = run_simulation(config)

    assert not df.empty
    assert {"round", "agent_id", "persona_type", "attitude", "institutional_trust", "risk_sensitivity", "conformity"}.issubset(df.columns)
    assert df["round"].max() == 6
