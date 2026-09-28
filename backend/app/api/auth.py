import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.core.request_guard import client_ip, request_guard
from app.db.session import get_db
from app.models.enums import UserRole
from app.schemas.auth import AdminLoginRequest, MaxAuthRequest, TokenResponse
from app.services.max_auth import InitDataError, validate_init_data
from app.services.user_upsert import upsert_max_user

router = APIRouter(tags=["auth"])


def _client_key(request: Request, endpoint: str) -> str:
    return f"{endpoint}:{client_ip(request)}"


@router.post("/auth/max", response_model=TokenResponse)
def auth_max(payload: MaxAuthRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        max_user = validate_init_data(payload.init_data)
    except InitDataError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не удалось подтвердить данные MAX") from exc

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


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, request: Request) -> TokenResponse:
    request_guard.enforce_rate(
        _client_key(request, "admin-login"),
        limit=settings.auth_rate_limit_per_minute,
        window_seconds=60,
    )
    if not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный пароль")
    token = create_access_token(subject=0, role=UserRole.admin.value, expire_days=1)
    return TokenResponse(access_token=token)
