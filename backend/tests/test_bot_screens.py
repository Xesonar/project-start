from sqlalchemy import select

from app.bot import screens
from app.bot.payload import decode
from app.db.session import SessionLocal
from app.models.user import User
from app.seed.run_seed import main as run_seed
from tests.test_max_auth import build_init_data


def _login_and_get_user(client, max_user_id: int) -> User:
    init_data = build_init_data(user={"id": max_user_id, "first_name": "Студент"})
    client.post("/auth/max", json={"init_data": init_data})

    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.max_user_id == max_user_id))
    finally:
        db.close()


def test_build_home_lists_pending_applications(client):
    run_seed()
    user = _login_and_get_user(client, 701)

    db = SessionLocal()
    try:
        text, buttons = screens.build_home(db, user)
    finally:
        db.close()

    assert "Найти проект" in text or any(
        b["text"] == "Найти проект" for row in buttons for b in row
    )
    assert any(b["type"] == "open_app" for row in buttons for b in row)


def test_build_projects_pagination(client):
    run_seed()

    db = SessionLocal()
    try:
        text_page0, buttons_page0 = screens.build_projects(db, 0)
        text_page1, _ = screens.build_projects(db, 1)
        text_page3, _ = screens.build_projects(db, 3)
    finally:
        db.close()

    # 12 seed projects, PAGE_SIZE=5: page 0 and 1 are full (5 each), page 2
    # has the remaining 2, page 3 is the first genuinely empty one.
    assert "стр. 1" in text_page0
    assert len(buttons_page0) == screens.PAGE_SIZE + 2  # projects + nav row + home row
    assert "стр. 2" in text_page1
    assert "больше нет" in text_page3


def test_build_project_detail_hides_already_applied_roles(client):
    run_seed()
    user = _login_and_get_user(client, 702)

    db = SessionLocal()
    try:
        from app.models.project import Project

        from app.models.enums import ProjectStatus

        project = db.scalar(
            select(Project).where(Project.status == ProjectStatus.open).order_by(Project.id.desc())
        )
        role_id = project.roles[0].id

        screens.build_apply_result(db, user, project.id, role_id)

        text, buttons = screens.build_project_detail(db, user, project.id, 0)
        apply_payloads = [
            b["payload"]
            for row in buttons
            for b in row
            if b["payload"].startswith("apply:")
        ]
        assert f"apply:{project.id}:{role_id}" not in apply_payloads
    finally:
        db.close()


def test_build_project_detail_does_not_expose_draft(client):
    run_seed()
    user = _login_and_get_user(client, 706)

    db = SessionLocal()
    try:
        from app.models.enums import ProjectStatus
        from app.models.project import Project

        project = db.scalar(select(Project).where(Project.status == ProjectStatus.open))
        project.status = ProjectStatus.draft
        db.commit()

        text, buttons = screens.build_project_detail(db, user, project.id, 0)
        assert "больше не найден" in text
        assert not any(
            button.get("payload", "").startswith("apply:")
            for row in buttons
            for button in row
        )
    finally:
        db.close()


def test_build_apply_result_success_then_duplicate(client):
    run_seed()
    user = _login_and_get_user(client, 703)

    db = SessionLocal()
    try:
        from app.models.project import Project

        from app.models.enums import ProjectStatus

        project = db.scalar(
            select(Project).where(Project.status == ProjectStatus.open).order_by(Project.id.desc())
        )
        role_id = project.roles[0].id

        text, _ = screens.build_apply_result(db, user, project.id, role_id)
        assert "отправлен" in text

        text_again, _ = screens.build_apply_result(db, user, project.id, role_id)
        assert "уже откликался" in text_again
    finally:
        db.close()


def test_build_my_applications_and_team_empty_states(client):
    run_seed()
    user = _login_and_get_user(client, 704)

    db = SessionLocal()
    try:
        text_apps, _ = screens.build_my_applications(db, user)
        assert "Пока нет откликов" in text_apps

        text_team, _ = screens.build_my_team(db, user)
        assert "не в команде" in text_team
    finally:
        db.close()


def test_route_dispatches_and_falls_back_to_home_on_garbage(client):
    run_seed()
    user = _login_and_get_user(client, 705)

    db = SessionLocal()
    try:
        text_a, _ = screens.route(db, user, decode("a"))
        assert "отклик" in text_a.lower()

        text_fallback, buttons_fallback = screens.route(db, user, decode("nonsense:x"))
        home_text, _ = screens.build_home(db, user)
        assert text_fallback == home_text
    finally:
        db.close()
