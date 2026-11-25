"""Principal required for recommendation lifecycle mutations.

The actor is the configured principal for a valid bearer token.
Clients cannot choose the actor in the request body.
"""

import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_principal(authorization: str | None = Header(default=None)) -> str:
    """Return the configured principal or reject the request."""
    configured = settings.api_token.strip()
    principal = settings.api_principal.strip()
    if not configured or not principal:
        raise HTTPException(status_code=401, detail="API principal is not configured")
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    supplied = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(supplied, configured):
        raise HTTPException(status_code=401, detail="Invalid token")
    return principal
