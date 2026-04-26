from fastapi import APIRouter, Depends, Form, HTTPException, Response, status

from ..auth import COOKIE_NAME, SESSION_TTL_SECONDS, issue_token, verify_credentials
from ..settings import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(
    response: Response,
    username: str = Form(),
    password: str = Form(),
    s: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not verify_credentials(s, username, password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    token = issue_token(s, username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"username": username}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}
