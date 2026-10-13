"""API-key authentication for write endpoints (CLAUDE.md §34/§36/§38).

Every state-changing endpoint depends on `WritePrincipal`. A request must send
a configured key in `X-API-Key`; the key's name becomes the audit-log actor,
so approvals are attributable to a person instead of a hardcoded default.

Fail closed: with no `API_KEYS` configured, every write is rejected. Read
endpoints stay open (demo data, no write capability).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from costlab.config import Settings, get_settings

API_KEY_HEADER = "X-API-Key"

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller; `name` is recorded as the audit actor."""

    name: str


def _match_identity(presented: str, identities: dict[str, str]) -> str | None:
    """Constant-time lookup: compare against every key so timing does not
    reveal which configured key (if any) shares a prefix."""
    matched: str | None = None
    for key, name in identities.items():
        if hmac.compare_digest(presented.encode(), key.encode()):
            matched = name
    return matched


def require_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    presented: Annotated[str | None, Security(_api_key_header)] = None,
) -> Principal:
    name = _match_identity(presented, settings.api_key_identities) if presented else None
    if name is None:
        # One message for missing, wrong, and unconfigured keys: do not reveal
        # whether write access is configured.
        raise HTTPException(
            status_code=401,
            detail=f"A valid {API_KEY_HEADER} header is required for this operation.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return Principal(name=name)


WritePrincipal = Annotated[Principal, Depends(require_principal)]
