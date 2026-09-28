from tests.test_max_auth import build_init_data


def test_project_without_skill_requirements_has_full_skill_match():
    from types import SimpleNamespace

    from app.services.recommendation import score_project

    project = SimpleNamespace(
        difficulty=SimpleNamespace(value="beginner"),
        roles=[],
        required_skills=[],
    )

    score, breakdown = score_project(project, {}, None)

    assert score == 0.4
    assert breakdown["skills"] == 0.4


def test_llm_explains_without_changing_deterministic_order(monkeypatch):
    from types import SimpleNamespace

    from app.services import recommendation

    def project(project_id: int):
        return SimpleNamespace(
            id=project_id,
            title=f"Project {project_id}",
            difficulty=SimpleNamespace(value="beginner"),
            roles=[],
            required_skills=[],
        )

    scored = [
        recommendation.ScoredProject(
            project=project(project_id),
            score=1 - project_id / 10,
            breakdown={"skills": 0.4},
        )
        for project_id in range(1, 7)
    ]
    monkeypatch.setattr(
        recommendation,
        "explain_recommendations",
        lambda *_args: [
            {"project_id": 1, "reason": "Тоже подходит"},
            {"project_id": 3, "reason": "Подходит по уровню"},
        ],
    )

    reasons = recommendation.explain_top_recommendations(scored, None, [], top_n=5)

    assert [item.project.id for item in scored] == [1, 2, 3, 4, 5, 6]
    assert reasons == {1: "Тоже подходит", 3: "Подходит по уровню"}


def _login(client, max_user_id: int) -> dict:
    init_data = build_init_data(user={"id": max_user_id, "first_name": "Студент"})
    resp = client.post("/auth/max", json={"init_data": init_data})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_recommendations_require_auth(client):
    resp = client.get("/projects/recommended")
    assert resp.status_code == 401


def test_recommendations_for_unknown_skills_only_return_beginner_projects(client):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _login(client, 555)

    resp = client.get("/projects/recommended", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert all(item["difficulty"] == "beginner" for item in body)
    assert all("без завышенных требований" in item["reason"] for item in body)
    scores = [item["score"] for item in body]
    assert scores == sorted(scores, reverse=True)


def test_recommendations_favor_matching_skills_and_role(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.skill import Skill
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _login(client, 556)

    db = SessionLocal()
    try:
        flutter_id = db.scalar(select(Skill.id).where(Skill.name == "Flutter"))
    finally:
        db.close()

    client.put("/me/skills", headers=headers, json=[{"skill_id": flutter_id, "level": "advanced"}])
    client.patch(
        "/me/profile",
        headers=headers,
        json={
            "specialty": "Разработка",
            "experience_level": "advanced",
            "preferred_role": "Mobile developer",
        },
    )

    resp = client.get("/projects/recommended", headers=headers)
    top = resp.json()[0]
    assert top["title"] == "Мобильный трекер привычек для студентов"
    assert top["score"] > 0.5


def test_beginner_profile_never_receives_advanced_project(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.skill import Skill
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _login(client, 557)
    db = SessionLocal()
    try:
        python_id = db.scalar(select(Skill.id).where(Skill.name == "Python"))
    finally:
        db.close()

    client.put(
        "/me/skills",
        headers=headers,
        json=[{"skill_id": python_id, "level": "beginner", "rating": 2}],
    )
    client.patch(
        "/me/profile",
        headers=headers,
        json={
            "specialty": "Разработка",
            "experience_level": "beginner",
            "preferred_role": "Backend developer",
        },
    )

    response = client.get("/projects/recommended", headers=headers)
    assert response.status_code == 200
    assert response.json()
    assert all(item["difficulty"] != "advanced" for item in response.json())
