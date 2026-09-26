"""Append-only audit trail helper (Phase 13, CLAUDE.md §23/§34)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from costlab.db.models import AuditLog


def record_audit(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any] | None = None,
    actor: str = "local-user",
    request_id: str | None = None,
) -> None:
    """Append one audit row. The application never updates or deletes these."""
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            request_id=request_id,
        )
    )
