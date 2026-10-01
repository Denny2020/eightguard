"""Bearer-token authentication against Keycloak (OIDC).

The API accepts only access tokens that are signed by the realm's current keys, issued by the
expected issuer, addressed to this API (aud), unexpired, and for a verified email address.
"""

from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException

from .config import settings

ALGORITHMS = ["RS256", "ES256"]
_jwks = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=3600, timeout=5)


@dataclass(frozen=True)
class Claims:
    sub: str
    email: str
    name: str


def signing_key(token: str):
    """Key for this token's `kid` from the realm JWKS (cached; tests replace this function)."""
    return _jwks.get_signing_key_from_jwt(token).key


def verify(token: str) -> Claims:
    try:
        payload = jwt.decode(
            token,
            signing_key(token),
            algorithms=ALGORITHMS,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            leeway=30,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError) as err:
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": "Bearer"}) from err
    if not payload.get("email") or payload.get("email_verified") is not True:
        raise HTTPException(403, "a verified email address is required")
    return Claims(sub=payload["sub"], email=payload["email"].lower(), name=payload.get("name", ""))


def current_claims(authorization: str | None = Header(default=None)) -> Claims:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "bearer token required", headers={"WWW-Authenticate": "Bearer"})
    return verify(token)
