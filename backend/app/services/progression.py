"""Small, deterministic progression rules for verified project experience."""

from app.models.enums import ProjectDifficulty

XP_BY_DIFFICULTY = {
    ProjectDifficulty.beginner: 30,
    ProjectDifficulty.intermediate: 60,
    ProjectDifficulty.advanced: 100,
}

# The first element is level one. A user always has at least that level.
LEVEL_THRESHOLDS = (0, 100, 250, 500)


def level_for_xp(xp: int) -> int:
    return sum(xp >= threshold for threshold in LEVEL_THRESHOLDS)


def next_level_xp(xp: int) -> int | None:
    return next((threshold for threshold in LEVEL_THRESHOLDS if threshold > xp), None)


def xp_reward(difficulty: ProjectDifficulty) -> int:
    return XP_BY_DIFFICULTY[difficulty]
