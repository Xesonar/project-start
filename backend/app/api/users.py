from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.profile import StudentProfile
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.schemas.user import (
    ProfileUpdate,
    SkillRead,
    UserRead,
    UserSkillIn,
    UserSkillRead,
)

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me/profile", response_model=UserRead)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.profile is None:
        user.profile = StudentProfile(user_id=user.id)
        db.add(user.profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user.profile, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.get("/skills", response_model=list[SkillRead])
def list_skills(db: Session = Depends(get_db)) -> list[Skill]:
    return list(db.scalars(select(Skill).order_by(Skill.category, Skill.name)))


@router.get("/me/skills", response_model=list[UserSkillRead])
def read_my_skills(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[UserSkill]:
    return list(db.scalars(select(UserSkill).where(UserSkill.user_id == user.id)))


@router.put("/me/skills", response_model=list[UserSkillRead])
def set_my_skills(
    payload: list[UserSkillIn],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSkill]:
    skill_ids = [item.skill_id for item in payload]
    if len(skill_ids) != len(set(skill_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate skill ids")

    existing_skill_ids = set(
        db.scalars(select(Skill.id).where(Skill.id.in_(skill_ids)))
    ) if skill_ids else set()
    missing_skill_ids = sorted(set(skill_ids) - existing_skill_ids)
    if missing_skill_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unknown skill ids: {missing_skill_ids}",
        )

    db.query(UserSkill).filter(UserSkill.user_id == user.id).delete()
    new_rows = [
        UserSkill(
            user_id=user.id,
            skill_id=item.skill_id,
            level=item.level,
            rating=item.rating
            if item.rating is not None
            else {"beginner": 2, "intermediate": 3, "advanced": 4}[item.level.value],
        )
        for item in payload
    ]
    db.add_all(new_rows)
    db.commit()
    return list(db.scalars(select(UserSkill).where(UserSkill.user_id == user.id)))
