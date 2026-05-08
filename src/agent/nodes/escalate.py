"""Escalation: structured unanswerable response when retrieval cannot support an answer."""

from __future__ import annotations

from typing import Any

from src.agent.state import AgentState, Answer


def run_escalate(state: AgentState) -> dict[str, Any]:
    """Return a safe refusal — no LLM generation from weak context (TRAP 7)."""
    if state.grade == "irrelevant":
        reason = (
            "Ik kan deze vraag niet beantwoorden op basis van de beschikbaar gestelde "
            "juridische bronnen. De gevonden fragmenten zijn niet toereikend of "
            "niet relevant."
        )
    else:
        reason = (
            "Ik kan deze vraag niet zeker beantwoorden met de huidige informatie uit de "
            "kennisbank. Een handmatige beoordeling of aanvullende gegevens zijn nodig."
        )
    if state.missing_info:
        reason = f"{reason} (Gemist: {state.missing_info})"
    answer = Answer(
        claims=[],
        confidence="low",
        unanswerable=True,
        unanswerable_reason=reason,
    )
    return {"final_answer": answer}
