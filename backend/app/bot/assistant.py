"""Text-command and AI orchestration for the MAX bot."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.bot import screens
from app.core.config import settings
from app.models.enums import ExperienceLevel, ProjectStatus, SkillLevel
from app.models.profile import StudentProfile
from app.models.project import Project, ProjectSkill
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.services import ai_client, bot_memory
from app.services.recommendation import explain_top_recommendations, recommend_projects


def conversation_key(*, is_private: bool, user: User, chat_id: int | None) -> str:
    return f"user:{user.max_user_id}" if is_private else f"chat:{chat_id or user.max_user_id}"


def _command(text: str) -> str | None:
    value = text.strip().lower()
    if not value.startswith("/"):
        return None
    return value.split()[0].split("@", 1)[0]


def _platform_context(db: Session) -> dict:
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.status == ProjectStatus.open)
            .options(
                selectinload(Project.organization),
                selectinload(Project.roles),
                selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
            )
            .order_by(Project.created_at.desc(), Project.id.desc())
            .limit(20)
        )
    )
    return {
        "open_projects": [
            {
                "id": project.id,
                "title": project.title,
                "organization": project.organization.name,
                "difficulty": project.difficulty.value,
                "roles": [role.title for role in project.roles],
                "skills": [item.skill.name for item in project.required_skills],
            }
            for project in projects
        ]
    }


def _profile_context(user: User) -> dict:
    profile = user.profile
    return {
        "profile": {
            "specialty": profile.specialty if profile else None,
            "experience_level": profile.experience_level.value if profile and profile.experience_level else None,
            "preferred_role": profile.preferred_role if profile else None,
            "goal": profile.goal if profile else None,
        },
        "skills": [
            {"name": item.skill.name, "rating": item.rating}
            for item in user.skills
            if item.skill is not None
        ],
    }


def _trim_string(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[:limit] if value else None


def _merge_profile(db: Session, user: User, consultation: ai_client.BotConsultation) -> list[str]:
    """Persist only explicit fields returned by the constrained AI response."""
    if not consultation.profile and not consultation.skills and not consultation.unknown_skills:
        return []

    if user.profile is None:
        user.profile = StudentProfile(user_id=user.id)
        db.add(user.profile)
    profile = user.profile
    changed: list[str] = []
    limits = {
        "university": 255,
        "specialty": 255,
        "about": 2000,
        "portfolio_url": 1024,
        "github_url": 1024,
        "goal": 255,
        "preferred_role": 255,
    }
    for field, limit in limits.items():
        value = _trim_string(consultation.profile.get(field), limit)
        if value is not None and getattr(profile, field) != value:
            setattr(profile, field, value)
            changed.append(field)
    course = consultation.profile.get("course")
    if isinstance(course, int) and 1 <= course <= 10 and profile.course != course:
        profile.course = course
        changed.append("course")
    experience = consultation.profile.get("experience_level")
    if isinstance(experience, str) and experience in ExperienceLevel._value2member_map_:
        level = ExperienceLevel(experience)
        if profile.experience_level != level:
            profile.experience_level = level
            changed.append("experience_level")

    skills_by_name = {
        skill.name.casefold(): skill for skill in db.scalars(select(Skill)).all()
    }
    current_skills = {item.skill_id: item for item in user.skills}
    for raw in consultation.skills:
        name = _trim_string(raw.get("name"), 100)
        rating = raw.get("rating")
        skill = skills_by_name.get(name.casefold()) if name else None
        if skill is None or not isinstance(rating, int) or not 1 <= rating <= 4:
            continue
        level = SkillLevel.beginner if rating <= 2 else SkillLevel.intermediate if rating == 3 else SkillLevel.advanced
        current = current_skills.get(skill.id)
        if current is None:
            db.add(UserSkill(user_id=user.id, skill_id=skill.id, level=level, rating=rating))
            changed.append(f"skill:{skill.name}")
        elif current.rating != rating:
            current.rating = rating
            current.level = level
            changed.append(f"skill:{skill.name}")

    unknown = []
    for item in consultation.unknown_skills:
        value = _trim_string(item, 100)
        if value and value.casefold() not in skills_by_name and value not in unknown:
            unknown.append(value)
    if unknown:
        note = "Указанные навыки вне справочника: " + ", ".join(unknown)
        existing = profile.about or ""
        if note not in existing:
            profile.about = (existing + ("\n" if existing else "") + note)[:2000]
            changed.append("unknown_skills")

    if changed:
        db.commit()
        db.refresh(user)
    return changed


def _profile_screen(user: User) -> tuple[str, screens.Buttons]:
    profile = user.profile
    if profile is None:
        return (
            "Профиль пока пуст. Расскажи, какую роль хочешь попробовать, что уже умеешь и какую цель ставишь.",
            [[{"type": "open_app", "text": "Открыть приложение"}], [screens._HOME_BUTTON]],
        )
    fields = [
        f"Роль: {profile.preferred_role or 'не указана'}",
        f"Цель: {profile.goal or 'не указана'}",
        f"Уровень: {profile.experience_level.value if profile.experience_level else 'не указан'}",
    ]
    skills = ", ".join(item.skill.name for item in user.skills if item.skill is not None) or "не указаны"
    return "Твой профиль:\n" + "\n".join(fields) + f"\nНавыки: {skills}", [[screens._HOME_BUTTON]]


def _recommendations_screen(db: Session, user: User) -> tuple[str, screens.Buttons]:
    scored, skills = recommend_projects(db, user.id, user.profile, limit=5)
    if not scored:
        return "Пока нет открытых проектов под твой профиль. Попробуй позже или расскажи больше о навыках.", [[screens._HOME_BUTTON]]
    reasons = explain_top_recommendations(scored, user.profile, skills, top_n=5)
    lines = ["Подходящие проекты:", ""]
    buttons: screens.Buttons = []
    for index, item in enumerate(scored, start=1):
        reason = reasons.get(item.project.id, "Совпадает с твоими текущими навыками и интересами.")
        lines.append(f"{index}. {item.project.title} — {round(item.score * 100)}%")
        lines.append(f"   {reason}")
        buttons.append(
            [{"type": "callback", "text": item.project.title[:40], "payload": f"pd:{item.project.id}:0"}]
        )
    buttons.append([screens._HOME_BUTTON])
    return "\n".join(lines), buttons


def _screen_for_intent(
    db: Session, user: User, intent: str
) -> tuple[str | None, screens.Buttons | None]:
    if intent == "home":
        return screens.build_home(db, user)
    if intent == "projects":
        return screens.build_projects(db, 0)
    if intent == "applications":
        return screens.build_my_applications(db, user)
    if intent == "team":
        return screens.build_my_team(db, user)
    if intent == "profile":
        return _profile_screen(user)
    if intent == "recommendations":
        return _recommendations_screen(db, user)
    if intent == "help":
        return (
            "Напиши, чего хочешь: найти проект, обновить профиль, посмотреть отклики или команду. Я понимаю и обычные фразы.",
            [[screens._HOME_BUTTON]],
        )
    if intent == "admin":
        return (
            "Открою страницу входа в админку. Для доступа нужен пароль администратора.",
            [[{"type": "link", "text": "Открыть админку", "url": f"{settings.public_app_url.rstrip('/')}/admin"}]],
        )
    return None, None


def _group_command_screen(db: Session, command: str) -> str:
    if command == "/projects":
        text, _buttons = screens.build_projects(db, 0)
        return text
    if command == "/help":
        return "Я отвечаю на текстовые вопросы и могу рассказать об открытых проектах. Личный подбор и отклики доступны в диалоге со мной."
    return "В группе я отвечаю как общий консультант. Для профиля, персонального подбора, откликов и команды напиши мне в личный диалог."


_COMMAND_INTENTS = {
    "/start": "home",
    "/menu": "home",
    "/projects": "projects",
    "/applications": "applications",
    "/team": "team",
    "/profile": "profile",
    "/admin": "admin",
    "/help": "help",
}


def handle_text(
    db: Session,
    *,
    user: User,
    text: str,
    is_private: bool,
    chat_id: int | None,
) -> tuple[str, screens.Buttons | None]:
    """Turn a MAX text event into an assistant reply and optional keyboard."""
    key = conversation_key(is_private=is_private, user=user, chat_id=chat_id)
    command = _command(text)
    if command == "/clear":
        bot_memory.clear(db, key)
        return "Контекст этого диалога очищен.", [[screens._HOME_BUTTON]] if is_private else None
    if command in _COMMAND_INTENTS:
        if is_private:
            screen_text, buttons = _screen_for_intent(db, user, _COMMAND_INTENTS[command])
            assert screen_text is not None
        else:
            screen_text, buttons = _group_command_screen(db, command), None
        bot_memory.remember(db, conversation_key=key, role="user", text=text, sender_max_user_id=user.max_user_id)
        bot_memory.remember(db, conversation_key=key, role="assistant", text=screen_text)
        return screen_text, buttons

    history = [
        {"role": item.role, "content": item.text}
        for item in bot_memory.recent_messages(db, key)
    ]
    context = _platform_context(db)
    if is_private:
        context.update(_profile_context(user))
    consultation = ai_client.consult_bot(
        text=text,
        history=history,
        platform_context=context,
        is_private=is_private,
    )
    if consultation is None:
        fallback = (
            "Сейчас не могу обработать сообщение через консультанта. Попробуй ещё раз или используй /menu."
        )
        bot_memory.remember(db, conversation_key=key, role="user", text=text, sender_max_user_id=user.max_user_id)
        bot_memory.remember(db, conversation_key=key, role="assistant", text=fallback)
        return fallback, [[screens._HOME_BUTTON]] if is_private else None

    changed = _merge_profile(db, user, consultation) if is_private else []
    screen_text, buttons = _screen_for_intent(db, user, consultation.intent) if is_private else (None, None)
    answer = consultation.reply
    if changed:
        answer += "\n\nЯ обновил профиль по твоему сообщению."
    if consultation.unknown_skills:
        answer += "\n\nНавыки вне справочника сохранены в описании, но пока не участвуют в подборе."
    if screen_text and consultation.intent != "chat":
        answer += "\n\n" + screen_text

    bot_memory.remember(db, conversation_key=key, role="user", text=text, sender_max_user_id=user.max_user_id)
    bot_memory.remember(db, conversation_key=key, role="assistant", text=answer)
    return answer[:4000], buttons
