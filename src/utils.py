"""Utility helpers for the PolicyPulse-Agent project."""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path


def summarize_reference_jsonl(path: str | Path, sample_size: int = 3) -> dict[str, object]:
    """Summarize a reference JSONL file for lightweight display in the UI."""
    file_path = Path(path)
    if not file_path.exists():
        return {
            "path": str(file_path),
            "exists": False,
            "question_count": 0,
            "answer_count": 0,
            "avg_answers_per_question": 0.0,
            "sample_titles": [],
        }

    question_count = 0
    answer_count = 0
    sample_titles: list[str] = []

    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            question_count += 1
            answer_count += len(record.get("answers", []))
            title = record.get("question_title", "")
            if title and len(sample_titles) < sample_size:
                sample_titles.append(title)

    avg_answers = answer_count / question_count if question_count else 0.0
    return {
        "path": str(file_path),
        "exists": True,
        "question_count": question_count,
        "answer_count": answer_count,
        "avg_answers_per_question": round(avg_answers, 2),
        "sample_titles": sample_titles,
    }


def get_reference_assets_summary() -> dict[str, object]:
    """Collect lightweight metadata about optional local reference assets."""
    sample_summary = summarize_reference_jsonl("sample_reference.jsonl")

    return {
        "sample": sample_summary,
    }


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value into a closed interval."""
    return max(low, min(high, value))


def attitude_to_label(attitude: float) -> str:
    """Convert a numeric attitude score into a qualitative label."""
    if attitude > 0.2:
        return "支持"
    if attitude < -0.2:
        return "反对"
    return "中立"


def safe_mean(values: Iterable[float]) -> float:
    """Compute mean safely for simple iterables."""
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)
