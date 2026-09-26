"""Thin client for DeepSeek explanations (OpenAI-compatible REST).

This is the optional explanation layer on top of the deterministic
recommendation engine (see services/recommendation.py). Every failure mode —
missing key, timeout, bad response, unexpected content — must degrade to
`None` so callers can fall back to the deterministic ranking without users
ever seeing a broken recommendations screen.
"""

import json
import logging

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
