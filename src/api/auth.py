"""Parse the ``X-User-Role`` header into the role list used by retrieval and cache."""

from __future__ import annotations

from fastapi import HTTPException, status


def roles_from_header(x_user_role: str | None) -> list[str]:
    """Split comma-separated roles; reject missing/empty header."""
    if x_user_role is None or not x_user_role.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Role header is required (comma-separated roles).",
        )
    roles = [r.strip().lower() for r in x_user_role.split(",") if r.strip()]
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Role must contain at least one non-empty role.",
        )
    return roles
