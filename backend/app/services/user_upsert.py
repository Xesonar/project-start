from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


def upsert_max_user(
    db: Session,
    *,
    max_user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Creates or updates a User from MAX-provided profile fields.

    Shared by /auth/max (trust comes from HMAC-validated initData) and the
    bot webhook (trust comes from the webhook secret instead) — both hand
    MAX user fields to the same upsert so there's one place that decides
    what a "name" is.
    """
    name = (
        " ".join(str(part).strip() for part in (first_name, last_name) if part).strip()
        or (str(username).strip() if username else "")
        or f"user{max_user_id}"
    )[:255]
    safe_avatar_url = str(avatar_url)[:1024] if avatar_url is not None else None

    user = db.scalar(select(User).where(User.max_user_id == max_user_id))
    if user is None:
        user = User(
            max_user_id=max_user_id,
            name=name,
            avatar_url=safe_avatar_url,
            role=UserRole.student,
        )
        db.add(user)
    else:
        user.name = name
        if avatar_url is not None:
            user.avatar_url = safe_avatar_url
    db.commit()
    db.refresh(user)
    return user
