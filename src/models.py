"""Pydantic models for the PolicyPulse-Agent project."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.scenarios import INTERVENTIONS, SCENARIOS


class AgentProfile(BaseModel):
    """A simplified public agent profile used in the simulation."""

    agent_id: str
    persona_type: str
    attitude: float = Field(ge=-1.0, le=1.0)
    institutional_trust: float = Field(ge=0.0, le=1.0)
    risk_sensitivity: float = Field(ge=0.0, le=1.0)
    benefit_sensitivity: float = Field(ge=0.0, le=1.0)
    conformity: float = Field(ge=0.0, le=1.0)
    openness: float = Field(ge=0.0, le=1.0)
    expression_strength: float = Field(ge=0.0, le=1.0)


class SimulationConfig(BaseModel):
    """Configuration for running the simulation."""

    scenario_name: str
    num_agents: int = Field(default=60, ge=10, le=300)
    num_rounds: int = Field(default=12, ge=3, le=50)
    intervention: str
    random_seed: int = Field(default=42, ge=0)

    @field_validator("scenario_name", "intervention")
    @classmethod
    def validate_not_empty(cls, value: str) -> str:
        """Ensure required string fields are non-empty."""
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("scenario_name")
    @classmethod
    def validate_scenario_name(cls, value: str) -> str:
        """Ensure the scenario name is one of the built-in options."""
        if value not in SCENARIOS:
            raise ValueError(f"unknown scenario_name: {value}")
        return value

    @field_validator("intervention")
    @classmethod
    def validate_intervention(cls, value: str) -> str:
        """Ensure the intervention is one of the built-in options."""
        if value not in INTERVENTIONS:
            raise ValueError(f"unknown intervention: {value}")
        return value
