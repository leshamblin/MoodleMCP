"""
Structured return models for tools.

These are plain dataclasses. FastMCP serializes a dataclass return into both
a human-readable text block and machine-readable ``structuredContent``, and
auto-generates an output schema from the field annotations. Using dataclasses
(rather than Pydantic) keeps the output path light and the schema stable;
incoming Moodle JSON is still parsed with the Pydantic models in this package.
"""

from dataclasses import dataclass, field


# --------------------------------------------------------------------- courses
@dataclass
class CourseSummary:
    id: int
    fullname: str
    shortname: str
    visible: bool
    startdate: int | None = None
    enddate: int | None = None


@dataclass
class CourseListResult:
    courses: list[CourseSummary]
    count: int


# ----------------------------------------------------------------------- users
@dataclass
class UserSummary:
    id: int
    fullname: str
    email: str | None = None
    username: str | None = None


# ---------------------------------------------------------------------- grading
@dataclass
class GradeSaveResult:
    course_id: int
    assignment_id: int  # activity instance id
    user_id: int
    grade: float
    feedback_saved: bool
    workflow_state: str


@dataclass
class BulkGradeResult:
    course_id: int
    assignment_id: int
    graded_count: int
    user_ids: list[int]


# --------------------------------------------------------------------- writes
@dataclass
class WriteResult:
    """Generic confirmation for a write that returns no id of its own."""
    operation: str
    ok: bool = True
    details: dict = field(default_factory=dict)


@dataclass
class CreatedResult:
    """Confirmation for a write that creates a record with an id."""
    operation: str
    id: int
    details: dict = field(default_factory=dict)
