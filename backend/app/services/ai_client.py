"""Thin client for DeepSeek explanations (OpenAI-compatible REST).

This is the optional explanation layer on top of the deterministic
recommendation engine (see services/recommendation.py). Every failure mode —
missing key, timeout, bad response, unexpected content — must degrade to
`None` so callers can fall back to the deterministic ranking without users
ever seeing a broken recommendations screen.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.deepseek.com/chat/completions"
_TIMEOUT_SECONDS = 8.0

_SYSTEM_PROMPT = (
    "Ты помогаешь студентам без опыта выбрать первый учебный проект. "
    "Тебе дан измеренный профиль студента и до 5 проектов, уже ранжированных "
    "алгоритмом. Не меняй их порядок. Для "
    "каждого напиши одну короткую причину на русском языке (не больше "
    "15 слов), почему он подходит именно этому студенту. Опирайся только на "
    "переданные навыки и разбивку баллов; не приписывай студенту навыки, "
    "которых нет в профиле. Не придумывай проекты. Отвечай строго в формате "
    'JSON: {"items": [{"project_id": <id>, "reason": "<причина>"}, ...]}.'
)

_BOT_SYSTEM_PROMPT = """Ты — дружелюбный текстовый консультант чат-бота «Старт».
Ты можешь отвечать на любые темы по-русски, но не утверждай, что проверял свежие
данные в интернете. Для вопросов о платформе используй только переданный каталог
и профиль. Не выдумывай проекты, статусы, навыки или выполненные действия.

Верни строго JSON-объект:
{
  "reply": "короткий полезный ответ, не более 1200 символов",
  "intent": "chat|home|projects|applications|team|profile|recommendations|help",
  "profile": {"optional explicit fields only": "..."},
  "skills": [{"name": "навык из справочника", "rating": 1..4}],
  "unknown_skills": ["явно названные, но отсутствующие в справочнике"]
}

Заполняй profile и skills только если пользователь в этой реплике явно сообщил
сведения о себе. Никогда не меняй profile или skills по догадке. intent описывает
то, что пользователь сейчас хочет открыть или сделать; действия с откликами не
выполняются из текста и должны быть предложены только кнопками. В групповом
чате profile, skills и unknown_skills всегда оставляй пустыми."""

_BOT_INTENTS = {"chat", "home", "projects", "applications", "team", "profile", "recommendations", "help"}
_PROFILE_FIELDS = {
    "university",
    "course",
    "specialty",
    "about",
    "experience_level",
    "portfolio_url",
    "github_url",
    "goal",
    "preferred_role",
}


@dataclass(frozen=True)
class BotConsultation:
    reply: str
    intent: str
    profile: dict[str, Any]
    skills: list[dict[str, Any]]
    unknown_skills: list[str]


def explain_recommendations(
    profile_summary: str, candidates: list[dict]
) -> list[dict] | None:
    """Returns [{"project_id": int, "reason": str}, ...] ranked best-first,
    or None if the LLM call failed or returned something unusable."""
    if not settings.deepseek_api_key or not candidates:
        return None

    candidate_ids = {c["project_id"] for c in candidates}
    user_prompt = (
        f"Профиль студента:\n{profile_summary}\n\n"
        f"Кандидаты:\n{json.dumps(candidates, ensure_ascii=False)}"
    )

    try:
        response = httpx.post(
            _API_URL,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        items = json.loads(content).get("items")

        if not isinstance(items, list) or not items:
            return None
        cleaned = []
        seen_ids = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                project_id = int(item["project_id"])
                reason = str(item["reason"]).strip()
            except (KeyError, TypeError, ValueError):
                continue
            if project_id not in candidate_ids or project_id in seen_ids or not reason:
                continue
            # The model is asked for 15 words, but output is still untrusted.
            # Keep cards compact even when the provider ignores the prompt.
            if len(reason) > 240:
                reason = reason[:237].rstrip() + "..."
            cleaned.append({"project_id": project_id, "reason": reason})
            seen_ids.add(project_id)
        return cleaned or None
    except Exception:
        logger.exception("DeepSeek recommendation explain call failed")
        return None


def consult_bot(
    *,
    text: str,
    history: list[dict[str, str]],
    platform_context: dict[str, Any],
    is_private: bool,
) -> BotConsultation | None:
    """Ask the existing DeepSeek integration to route and answer bot text.

    The model is deliberately constrained to a small JSON result. Parsing and
    database writes remain deterministic in the caller; malformed model output
    therefore has the same safe fallback as an unavailable model.
    """
    if not settings.deepseek_api_key or not text.strip():
        return None

    user_context = {
        "is_private_dialog": is_private,
        "platform_context": platform_context,
        "message": text[:4000],
    }
    messages = [{"role": "system", "content": _BOT_SYSTEM_PROMPT}]
    messages.extend(
        {"role": item["role"], "content": item["content"][:4000]}
        for item in history[-10:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    )
    messages.append({"role": "user", "content": json.dumps(user_context, ensure_ascii=False)})

    try:
        response = httpx.post(
            _API_URL,
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        raw = json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception:
        logger.exception("DeepSeek bot consultation failed")
        return None

    reply = str(raw.get("reply") or "").strip()
    if not reply:
        return None
    intent = raw.get("intent") if raw.get("intent") in _BOT_INTENTS else "chat"
    profile = raw.get("profile") if is_private and isinstance(raw.get("profile"), dict) else {}
    profile = {key: value for key, value in profile.items() if key in _PROFILE_FIELDS}
    skills = raw.get("skills") if is_private and isinstance(raw.get("skills"), list) else []
    unknown_skills = (
        raw.get("unknown_skills")
        if is_private and isinstance(raw.get("unknown_skills"), list)
        else []
    )
    return BotConsultation(
        reply=reply[:1200],
        intent=intent,
        profile=profile,
        skills=[item for item in skills if isinstance(item, dict)][:20],
        unknown_skills=[str(item).strip()[:100] for item in unknown_skills if str(item).strip()][:20],
    )
