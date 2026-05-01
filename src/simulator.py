"""Simulation engine for public attitude evolution."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from src.models import AgentProfile, SimulationConfig
from src.scenarios import get_intervention, get_persona_templates, get_scenario
from src.utils import attitude_to_label, clamp, safe_mean


PERSONA_RESPONSE_PROFILES: dict[str, dict[str, float]] = {
    "技术乐观型": {
        "baseline_bias": 0.10,
        "caution_multiplier": 0.70,
        "trust_multiplier": 0.95,
        "social_multiplier": 0.90,
        "anchor_strength": 0.90,
    },
    "风险敏感型": {
        "baseline_bias": -0.11,
        "caution_multiplier": 1.25,
        "trust_multiplier": 0.70,
        "social_multiplier": 0.80,
        "anchor_strength": 1.10,
    },
    "制度信任型": {
        "baseline_bias": 0.02,
        "caution_multiplier": 0.90,
        "trust_multiplier": 1.35,
        "social_multiplier": 0.85,
        "anchor_strength": 0.95,
    },
    "权益保护型": {
        "baseline_bias": -0.10,
        "caution_multiplier": 1.30,
        "trust_multiplier": 0.75,
        "social_multiplier": 0.75,
        "anchor_strength": 1.05,
    },
    "功利效率型": {
        "baseline_bias": 0.08,
        "caution_multiplier": 0.82,
        "trust_multiplier": 0.92,
        "social_multiplier": 0.90,
        "anchor_strength": 0.85,
    },
    "中立观望型": {
        "baseline_bias": 0.00,
        "caution_multiplier": 1.00,
        "trust_multiplier": 0.88,
        "social_multiplier": 1.35,
        "anchor_strength": 0.70,
    },
}


def create_agents(config: SimulationConfig) -> list[AgentProfile]:
    """Create a mixed population of agents from built-in persona templates."""
    rng = np.random.default_rng(config.random_seed)
    templates = get_persona_templates()
    persona_names = list(templates.keys())

    base_count = config.num_agents // len(persona_names)
    remainder = config.num_agents % len(persona_names)

    agents: list[AgentProfile] = []
    agent_index = 1
    for i, persona_name in enumerate(persona_names):
        count = base_count + (1 if i < remainder else 0)
        template = templates[persona_name]
        for _ in range(count):
            agents.append(
                AgentProfile(
                    agent_id=f"A{agent_index:03d}",
                    persona_type=persona_name,
                    attitude=clamp(template["attitude"] + rng.normal(0, 0.12), -1.0, 1.0),
                    institutional_trust=clamp(
                        template["institutional_trust"] + rng.normal(0, 0.08), 0.0, 1.0
                    ),
                    risk_sensitivity=clamp(
                        template["risk_sensitivity"] + rng.normal(0, 0.07), 0.0, 1.0
                    ),
                    benefit_sensitivity=clamp(
                        template["benefit_sensitivity"] + rng.normal(0, 0.07), 0.0, 1.0
                    ),
                    conformity=clamp(template["conformity"] + rng.normal(0, 0.08), 0.0, 1.0),
                    openness=clamp(template["openness"] + rng.normal(0, 0.08), 0.0, 1.0),
                    expression_strength=clamp(
                        template["expression_strength"] + rng.normal(0, 0.08), 0.0, 1.0
                    ),
                )
            )
            agent_index += 1

    rng.shuffle(agents)
    return agents


def update_attitude(
    agent: AgentProfile,
    neighbors: list[AgentProfile],
    scenario: Any,
    intervention: dict[str, float | str],
    rng: np.random.Generator,
) -> AgentProfile:
    """Update one agent's attitude with damping, heterogeneity, and social influence."""
    original_attitude = agent.attitude
    neighbor_mean = safe_mean(neighbor.attitude for neighbor in neighbors)
    persona_profile = PERSONA_RESPONSE_PROFILES[agent.persona_type]
    persona_anchor = get_persona_templates()[agent.persona_type]["attitude"]
    intervention_name = str(intervention.get("name", ""))

    benefit_pressure = scenario.benefit_level * agent.benefit_sensitivity * 0.22
    risk_pressure = scenario.risk_level * agent.risk_sensitivity * 0.24 * persona_profile["caution_multiplier"]
    policy_signal = (
        scenario.policy_valence * 0.18
        + benefit_pressure
        - risk_pressure
        + persona_profile["baseline_bias"] * 0.08
    )

    intervention_signal = (
        float(intervention["benefit_shift"]) * agent.benefit_sensitivity * 0.10
        - float(intervention["risk_shift"]) * agent.risk_sensitivity * 0.10
    )
    trust_signal = (
        float(intervention["trust_shift"])
        * scenario.trust_relevance
        * agent.institutional_trust
        * persona_profile["trust_multiplier"]
        * 0.15
    )
    if intervention_name == "官方政策解释" and agent.persona_type == "制度信任型":
        trust_signal += 0.035 * agent.institutional_trust
    if intervention_name == "官方政策解释" and agent.persona_type in {"风险敏感型", "权益保护型"}:
        trust_signal *= 0.75

    info_impact = (policy_signal + intervention_signal + trust_signal) * (0.07 + agent.openness * 0.08)
    social_gap = neighbor_mean - original_attitude
    social_weight = (
        0.04
        + agent.conformity * 0.10
        + persona_profile["social_multiplier"] * 0.03
        + float(intervention["social_temperature"]) * 0.04
    )
    social_impact = social_gap * social_weight

    anchor_pull = (persona_anchor - original_attitude) * (0.03 + persona_profile["anchor_strength"] * 0.025)

    noise_scale = max(0.008, 0.028 - agent.expression_strength * 0.008)
    random_noise = rng.normal(0, noise_scale)

    raw_delta = info_impact + social_impact + anchor_pull + random_noise
    same_direction_extreme_push = np.sign(raw_delta) == np.sign(original_attitude) and abs(original_attitude) > 0.15
    directional_damping = 1.0 - (0.35 * abs(original_attitude) if same_direction_extreme_push else 0.10 * abs(original_attitude))
    baseline_damping = max(0.35, 1.0 - 0.45 * abs(original_attitude))
    capped_delta = clamp(raw_delta * directional_damping * baseline_damping, -0.16, 0.16)

    new_attitude = clamp(original_attitude + capped_delta, -1.0, 1.0)
    return agent.model_copy(update={"attitude": new_attitude})


def run_simulation(config: SimulationConfig) -> pd.DataFrame:
    """Run the multi-agent simulation and return round-level panel data."""
    rng = np.random.default_rng(config.random_seed)
    scenario = get_scenario(config.scenario_name)
    intervention = {"name": config.intervention, **get_intervention(config.intervention)}
    agents = create_agents(config)

    records: list[dict[str, float | str | int]] = []

    for round_index in range(config.num_rounds + 1):
        for agent in agents:
            records.append(
                {
                    "round": round_index,
                    "agent_id": agent.agent_id,
                    "persona_type": agent.persona_type,
                    "attitude": agent.attitude,
                    "institutional_trust": agent.institutional_trust,
                    "risk_sensitivity": agent.risk_sensitivity,
                    "benefit_sensitivity": agent.benefit_sensitivity,
                    "conformity": agent.conformity,
                    "openness": agent.openness,
                    "expression_strength": agent.expression_strength,
                    "stance": attitude_to_label(agent.attitude),
                }
            )

        if round_index == config.num_rounds:
            break

        updated_agents: list[AgentProfile] = []
        for agent in agents:
            candidate_neighbors = [other for other in agents if other.agent_id != agent.agent_id]
            sample_size = min(len(candidate_neighbors), max(3, len(agents) // 8))
            selected_indices = rng.choice(len(candidate_neighbors), size=sample_size, replace=False)
            neighbors = [candidate_neighbors[index] for index in np.atleast_1d(selected_indices)]
            updated_agents.append(update_attitude(agent, neighbors, scenario, intervention, rng))
        agents = updated_agents

    df = pd.DataFrame(records)
    df["stance"] = pd.Categorical(df["stance"], categories=["支持", "中立", "反对"], ordered=True)
    return df


def summarize_final_distribution(df: pd.DataFrame) -> dict[str, int]:
    """Return the stance counts from the final round."""
    final_round = df["round"].max()
    counts = Counter(df.loc[df["round"] == final_round, "stance"])
    return {label: counts.get(label, 0) for label in ["支持", "中立", "反对"]}
