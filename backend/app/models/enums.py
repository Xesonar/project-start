import enum


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class ExperienceLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class SkillLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ProjectDifficulty(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    recruitment_closed = "recruitment_closed"
    in_progress = "in_progress"
    completed = "completed"


class ProjectFormat(str, enum.Enum):
    online = "online"
    offline = "offline"
    hybrid = "hybrid"


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"
    leave_requested = "leave_requested"


class ProjectSubmissionStatus(str, enum.Enum):
    submitted = "submitted"
    revision_requested = "revision_requested"
    approved = "approved"
    rejected = "rejected"
