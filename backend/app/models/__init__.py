# Import every model module here so Base.metadata is fully populated for
# Alembic autogenerate. Import this package (not app.db.base) when you need
# "all models" — importing models from db/base.py would create a cycle,
# since each model imports Base from there.
from app.models.user import User  # noqa: F401
from app.models.profile import StudentProfile  # noqa: F401
from app.models.skill import Skill, UserSkill  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.project import Project, ProjectRole, ProjectSkill  # noqa: F401
from app.models.application import Application  # noqa: F401
from app.models.team import Team, TeamMember  # noqa: F401
from app.models.result import ProjectResult, ParticipationConfirmation  # noqa: F401
