"""LangGraph CRAG agent: decompose → retrieve → grade → generate or correct.

RBAC travels only via `user_roles` into the retrieval node; the LLM never
filters permissions (TRAPS.md TRAP 2). Citations are structurally enforced
before any answer is returned (TRAP 6).
"""

from __future__ import annotations

from src.agent.graph import AgentNodeOverrides, build_agent_graph, route_after_grade
from src.agent.state import (
    AgentState,
    Answer,
    Citation,
    CitedClaim,
    DecompositionResult,
    GradeResult,
)

__all__ = [
    "AgentNodeOverrides",
    "AgentState",
    "Answer",
    "Citation",
    "CitedClaim",
    "DecompositionResult",
    "GradeResult",
    "build_agent_graph",
    "route_after_grade",
]
