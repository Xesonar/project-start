from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.skill import Skill
from app.seed.run_seed import main as run_seed
from tests.test_max_auth import build_init_data


def _headers(client) -> dict:
    init_data = build_init_data(user={"id": 901, "first_name": "Студент"})
    response = client.post("/auth/max", json={"init_data": init_data})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_duplicate_skill_ids_are_rejected(client):
    run_seed()
    headers = _headers(client)
    with SessionLocal() as db:
        skill_id = db.scalar(select(Skill.id).order_by(Skill.id))

    response = client.put(
        "/me/skills",
        headers=headers,
        json=[
            {"skill_id": skill_id, "level": "beginner"},
            {"skill_id": skill_id, "level": "advanced"},
        ],
    )
    assert response.status_code == 422


def test_unknown_skill_id_is_rejected_without_losing_existing_skills(client):
    run_seed()
    headers = _headers(client)
    with SessionLocal() as db:
        skill_id = db.scalar(select(Skill.id).order_by(Skill.id))

    saved = client.put(
        "/me/skills",
        headers=headers,
        json=[{"skill_id": skill_id, "level": "intermediate"}],
    )
    assert saved.status_code == 200

    rejected = client.put(
        "/me/skills",
        headers=headers,
        json=[{"skill_id": 999999, "level": "advanced"}],
    )
    assert rejected.status_code == 422

    current = client.get("/me/skills", headers=headers)
    assert current.status_code == 200
    assert [item["skill"]["id"] for item in current.json()] == [skill_id]
    assert current.json()[0]["rating"] == 3


def test_five_step_rating_is_persisted(client):
    run_seed()
    headers = _headers(client)
    with SessionLocal() as db:
        skill_id = db.scalar(select(Skill.id).order_by(Skill.id))

    response = client.put(
        "/me/skills",
        headers=headers,
        json=[{"skill_id": skill_id, "level": "advanced", "rating": 4}],
    )
    assert response.status_code == 200
    assert response.json()[0]["rating"] == 4
