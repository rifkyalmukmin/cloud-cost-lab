"""Authentication for write endpoints (CLAUDE.md §34/§36/§38).

Every state-changing endpoint depends on `WritePrincipal`. Two credential
kinds are accepted, both resolving to an actor name that is recorded as the
audit-log actor:

1. **API key** — `X-API-Key: <key>`; keys are configured as `API_KEYS`
   (`name:key,...`) and looked up in constant time.
2. **JWT bearer** — `Authorization: Bearer <token>`; an HS256 token signed
   with `JWT_SECRET`, with a `sub` claim carrying the actor name and an
   `exp` claim (short-lived tokens). Implemented with the standard library
   only — no new dependency.

Fail closed: with no credentials configured, every write is rejected. Read
endpoints stay open (demo data, no write capability). One generic 401
message for every failure mode: do not reveal which part of the credential
was wrong, or whether write access is configured at all.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer

from costlab.config import Settings, get_settings

API_KEY_HEADER = "X-API-Key"
BEARER_SCHEME = "bearer"
JWT_ALGORITHM = "HS256"
ACTOR_MAX_LENGTH = 64
_ACTOR_PATTERN_NAME = "actor must match [A-Za-z0-9._-]{1,64}"

_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)
_bearer_credentials = HTTPBearer(auto_error=False)

_UNAUTHORIZED = f"A valid {API_KEY_HEADER} header or Bearer token is required for this operation."


class _CredentialError(Exception):
    """Internal: any bearer-token failure (mapped to the generic 401)."""


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


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_hs256(token: str, secret: str) -> dict[str, Any]:
    """Verify an HS256 JWT with the standard library. Fails closed on
    malformed input, wrong algorithm, bad signature, missing `exp`, and
    expired tokens."""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise _CredentialError("malformed token") from exc

    try:
        header = json.loads(_b64url_decode(header_b64))
        claims = json.loads(_b64url_decode(payload_b64))
        signature = _b64url_decode(signature_b64)
    except (ValueError, json.JSONDecodeError) as exc:
        raise _CredentialError("malformed token") from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise _CredentialError("unsupported algorithm")

    expected = hmac.new(
        secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise _CredentialError("bad signature")

    exp = claims.get("exp")
    if not isinstance(exp, int | float):
        raise _CredentialError("missing exp")
    if time.time() >= exp:
        raise _CredentialError("expired token")

    if not isinstance(claims, dict):
        raise _CredentialError("malformed token payload")
    return claims


def _actor_from_claims(claims: dict[str, Any]) -> str:
    import re

    sub = claims.get("sub")
    if not isinstance(sub, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", sub):
        raise _CredentialError(_ACTOR_PATTERN_NAME)
    return sub


def _principal_from_bearer(token: str, settings: Settings) -> Principal:
    if not settings.jwt_secret:
        # Fail closed: bearer credentials are worthless without a configured
        # signing secret, and saying so must not confirm that API keys exist.
        raise _CredentialError("bearer authentication is not configured")
    claims = _decode_hs256(token, settings.jwt_secret)
    return Principal(name=_actor_from_claims(claims))


def require_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    presented_api_key: Annotated[str | None, Security(_api_key_header)] = None,
    bearer: Annotated[Any, Security(_bearer_credentials)] = None,
) -> Principal:
    try:
        if bearer is not None and bearer.scheme.lower() == BEARER_SCHEME:
            return _principal_from_bearer(bearer.credentials, settings)
    except _CredentialError:
        # One generic message for every bearer failure mode.
        raise HTTPException(
            status_code=401,
            detail=_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    name = (
        _match_identity(presented_api_key, settings.api_key_identities)
        if presented_api_key
        else None
    )
    if name is None:
        raise HTTPException(
            status_code=401,
            detail=_UNAUTHORIZED,
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return Principal(name=name)


WritePrincipal = Annotated[Principal, Depends(require_principal)]
