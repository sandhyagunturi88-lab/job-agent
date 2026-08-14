"""Supabase JWT auth.

Verifies the Supabase access token (HS256, audience "authenticated").
In development without SUPABASE_JWT_SECRET configured, requests resolve
to a fixed demo user so the graph can be exercised end-to-end locally.
"""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not settings.supabase_jwt_secret:
        if settings.is_dev:
            return CurrentUser(id=DEMO_USER_ID, email="demo@jobpilot.uk")
        raise HTTPException(status_code=500, detail="Auth not configured")

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    return CurrentUser(id=payload["sub"], email=payload.get("email"))
