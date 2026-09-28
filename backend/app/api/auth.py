import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.core.request_guard import client_ip, request_guard
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.auth import AdminLoginRequest, DemoAuthRequest, MaxAuthRequest, TokenResponse
from app.services.max_auth import InitDataError, validate_init_data
from app.services.user_upsert import (
    cleanup_stale_demo_users,
    ensure_demo_portfolio_confirmation,
    ensure_demo_user,
    upsert_max_user,
)

router = APIRouter(tags=["auth"])


def _client_key(request: Request, endpoint: str) -> str:
    return f"{endpoint}:{client_ip(request)}"


@router.post("/auth/max", response_model=TokenResponse)
def auth_max(payload: MaxAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        max_user = validate_init_data(payload.init_data)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid init data: {exc}") from exc

    user = upsert_max_user(
        db,
        max_user_id=int(max_user["id"]),
        first_name=max_user.get("first_name"),
        last_name=max_user.get("last_name"),
        username=max_user.get("username"),
        avatar_url=max_user.get("photo_url"),
    )

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


# Skills the demo student "already knows" — picked to line up with several
# seeded beginner projects so the very first recommendation screen looks alive.
_DEMO_SKILL_NAMES = ("JavaScript", "HTML/CSS", "React", "Figma", "Git", "Python")


@router.post("/auth/demo", response_model=TokenResponse)
def auth_demo(
    request: Request,
    payload: DemoAuthRequest | None = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Passwordless web entry point for judges/organizers without a MAX account.

    The demo student is a real User row with a filled profile, so every screen
    (AI recommendations, applications, portfolio) works identically to a MAX
    login. Disabled unless DEMO_MODE=true.
    """
    if not settings.demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo mode is disabled")
    request_guard.enforce_rate(
        _client_key(request, "auth-demo"),
        limit=settings.auth_rate_limit_per_minute,
        window_seconds=60,
    )

    demo_max_user_id = settings.demo_max_user_id
    if payload is not None:
        digest = int.from_bytes(
            hashlib.sha256(payload.session_id.encode("utf-8")).digest()[:8],
            "big",
        )
        demo_max_user_id = -max(2, digest & ((1 << 63) - 1))

    cleanup_stale_demo_users(db, keep_max_user_id=demo_max_user_id)

    user = ensure_demo_user(
        db,
        max_user_id=demo_max_user_id,
        skill_names=_DEMO_SKILL_NAMES,
    )
    ensure_demo_portfolio_confirmation(db, user)
    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, request: Request) -> TokenResponse:
    request_guard.enforce_rate(
        _client_key(request, "admin-login"),
        limit=settings.auth_rate_limit_per_minute,
        window_seconds=60,
    )
    if not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный пароль")
    token = create_access_token(subject=0, role=UserRole.admin.value)
    return TokenResponse(access_token=token)
