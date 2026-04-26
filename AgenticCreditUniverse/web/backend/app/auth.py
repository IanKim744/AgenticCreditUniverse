from __future__ import annotations

import hmac
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .settings import Settings, get_settings

COOKIE_NAME = "creditu_session"
SESSION_TTL_SECONDS = 60 * 60 * 12  # 12h


def _signer(s: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(s.session_secret, salt="creditu-v1")


def issue_token(s: Settings, username: str) -> str:
    return _signer(s).dumps({"u": username})


def verify_credentials(s: Settings, username: str, password: str) -> bool:
    return hmac.compare_digest(username, s.login_username) and hmac.compare_digest(password, s.login_password)


def require_session(request: Request, s: Settings = Depends(get_settings)) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthenticated")
    try:
        payload = _signer(s).loads(token, max_age=SESSION_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session_expired")
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    if not isinstance(payload, dict) or not payload.get("u"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="malformed_session")
    return payload
