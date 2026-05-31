"""
Quiz tools - READ and WRITE operations for quizzes and quiz attempts.

Note on answering quizzes: the field names in `answers` for save/submit are
question-type specific (e.g. ``q<attemptid>:<slot>_answer``). Call
moodle_get_quiz_attempt_data first to discover the exact field names for the
current attempt, then pass them as {name, value} entries.
"""

from dataclasses import dataclass
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver


@dataclass
class Quiz:
    id: int                    # quiz instance id
    coursemodule: int | None   # cmid
    course: int | None
    name: str
    timeopen: int | None = None
    timeclose: int | None = None
    timelimit: int | None = None


@dataclass
class QuizList:
    quizzes: list[Quiz]
    count: int


@dataclass
class QuizAttempt:
    id: int
    quiz: int | None = None
    state: str | None = None
    attempt: int | None = None
    timestart: int | None = None
    timefinish: int | None = None
    sumgrades: float | None = None


@dataclass
class QuizAttemptList:
    quiz_id: int
    attempts: list[QuizAttempt]
    count: int


@dataclass
class AttemptQuestion:
    slot: int | None
    type: str | None
    status: str | None
    html: str | None = None


@dataclass
class AttemptData:
    attempt_id: int
    page: int
    questions: list[AttemptQuestion]


@dataclass
class StartedAttempt:
    attempt_id: int
    quiz_id: int
    state: str | None = None


@dataclass
class SaveResult:
    attempt_id: int
    status: bool


@dataclass
class SubmitResult:
    attempt_id: int
    state: str | None


def _normalize_answer_data(answers: list[dict]) -> list[dict]:
    """
    Accept either [{"name": ..., "value": ...}, ...] (preferred) or
    [{"<fieldname>": "<value>"}, ...] and normalize to the {name, value}
    list shape Moodle's quiz `data` parameter expects.
    """
    out: list[dict] = []
    for a in answers:
        if "name" in a and "value" in a:
            out.append({"name": a["name"], "value": a["value"]})
        else:
            for k, v in a.items():
                out.append({"name": k, "value": v})
    return out


@mcp.tool(
    name="moodle_get_quizzes",
    description=(
        "Get all quizzes in a course. REQUIRED: course (id, shortname, or "
        "idnumber). Returns each quiz's instance id, course-module id (cmid), "
        "name, and timing."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_quizzes(
    course: Annotated[int | str, Field(description="Course id, shortname, or idnumber")],
    ctx: Context = None,
) -> QuizList:
    moodle = get_moodle_client(ctx)
    cid = await get_resolver(ctx).course_id(course)
    data = await moodle.call("mod_quiz_get_quizzes_by_courses", {"courseids": [cid]})
    raw = data.get("quizzes", []) if isinstance(data, dict) else []
    quizzes = [
        Quiz(
            id=q.get("id"),
            coursemodule=q.get("coursemodule"),
            course=q.get("course"),
            name=q.get("name", ""),
            timeopen=q.get("timeopen"),
            timeclose=q.get("timeclose"),
            timelimit=q.get("timelimit"),
        )
        for q in raw
    ]
    return QuizList(quizzes=quizzes, count=len(quizzes))


@mcp.tool(
    name="moodle_get_quiz_attempts",
    description=(
        "Get a user's attempts for a quiz. REQUIRED: quiz_id (the quiz "
        "instance id). Optional: user (id/username/email; omit for current "
        "user), status (all/finished/unfinished)."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_quiz_attempts(
    quiz_id: Annotated[int, Field(description="Quiz instance id", gt=0)],
    user: Annotated[int | str | None, Field(description="User id/username/email; omit for current user")] = None,
    status: Annotated[str, Field(description="Attempt status: all, finished, or unfinished")] = "all",
    ctx: Context = None,
) -> QuizAttemptList:
    moodle = get_moodle_client(ctx)
    uid = await get_resolver(ctx).user_id(user)
    data = await moodle.call(
        "mod_quiz_get_user_attempts",
        {"quizid": quiz_id, "userid": uid, "status": status},
    )
    raw = data.get("attempts", []) if isinstance(data, dict) else []
    attempts = [
        QuizAttempt(
            id=a.get("id"),
            quiz=a.get("quiz"),
            state=a.get("state"),
            attempt=a.get("attempt"),
            timestart=a.get("timestart"),
            timefinish=a.get("timefinish"),
            sumgrades=a.get("sumgrades"),
        )
        for a in raw
    ]
    return QuizAttemptList(quiz_id=quiz_id, attempts=attempts, count=len(attempts))


@mcp.tool(
    name="moodle_get_quiz_attempt_data",
    description=(
        "Get the questions and form-field names for an in-progress quiz "
        "attempt. REQUIRED: attempt_id. Optional: page (default 0). Call this "
        "BEFORE saving/submitting answers to discover the exact field names "
        "(the answer field names are question-type specific)."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_quiz_attempt_data(
    attempt_id: Annotated[int, Field(description="Quiz attempt id", gt=0)],
    page: Annotated[int, Field(description="Page number", ge=0)] = 0,
    ctx: Context = None,
) -> AttemptData:
    moodle = get_moodle_client(ctx)
    data = await moodle.call(
        "mod_quiz_get_attempt_data", {"attemptid": attempt_id, "page": page}
    )
    raw = data.get("questions", []) if isinstance(data, dict) else []
    questions = [
        AttemptQuestion(
            slot=q.get("slot"),
            type=q.get("type"),
            status=q.get("status"),
            html=q.get("html"),
        )
        for q in raw
    ]
    return AttemptData(attempt_id=attempt_id, page=page, questions=questions)


@mcp.tool(
    name="moodle_start_quiz_attempt",
    description=(
        "Start a new quiz attempt. REQUIRED: course_id, quiz_id (the quiz "
        "instance id). WRITE OPERATION - whitelisted courses only. Returns the "
        "new attempt id for saving/submitting answers."
    ),
    tags={"write", "quiz"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_start_quiz_attempt(
    course_id: Annotated[int, Field(description="Course ID (whitelisted)", gt=0)],
    quiz_id: Annotated[int, Field(description="Quiz instance id", gt=0)],
    ctx: Context = None,
) -> StartedAttempt:
    moodle = get_moodle_client(ctx)
    data = await moodle.call("mod_quiz_start_attempt", {"quizid": quiz_id})
    attempt = data.get("attempt", {}) if isinstance(data, dict) else {}
    return StartedAttempt(
        attempt_id=attempt.get("id", 0),
        quiz_id=quiz_id,
        state=attempt.get("state"),
    )


@mcp.tool(
    name="moodle_save_quiz_answers",
    description=(
        "Save answers during a quiz attempt (auto-save, not final). REQUIRED: "
        "course_id, attempt_id, answers (list of {name, value} entries). Get "
        "the field names from moodle_get_quiz_attempt_data first. WRITE "
        "OPERATION - whitelisted courses only."
    ),
    tags={"write", "quiz"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_save_quiz_answers(
    course_id: Annotated[int, Field(description="Course ID (whitelisted)", gt=0)],
    attempt_id: Annotated[int, Field(description="Quiz attempt id", gt=0)],
    answers: Annotated[
        list[dict],
        Field(description="List of {name, value} form entries from get_quiz_attempt_data"),
    ],
    ctx: Context = None,
) -> SaveResult:
    moodle = get_moodle_client(ctx)
    data = _normalize_answer_data(answers)
    result = await moodle.call(
        "mod_quiz_save_attempt", {"attemptid": attempt_id, "data": data}
    )
    status = bool(result.get("status")) if isinstance(result, dict) else True
    return SaveResult(attempt_id=attempt_id, status=status)


@mcp.tool(
    name="moodle_submit_quiz",
    description=(
        "Submit a quiz attempt for grading (final, cannot be undone). "
        "REQUIRED: course_id, attempt_id. Optional: answers (list of "
        "{name, value}) to submit with the finish. WRITE OPERATION - "
        "DESTRUCTIVE - whitelisted courses only."
    ),
    tags={"write", "quiz", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission("course_id")
async def moodle_submit_quiz(
    course_id: Annotated[int, Field(description="Course ID (whitelisted)", gt=0)],
    attempt_id: Annotated[int, Field(description="Quiz attempt id", gt=0)],
    answers: Annotated[
        list[dict] | None,
        Field(description="Optional final {name, value} answers to submit"),
    ] = None,
    ctx: Context = None,
) -> SubmitResult:
    moodle = get_moodle_client(ctx)
    params: dict = {"attemptid": attempt_id, "finishattempt": 1, "timeup": 0}
    if answers:
        params["data"] = _normalize_answer_data(answers)
    result = await moodle.call("mod_quiz_process_attempt", params)
    state = result.get("state") if isinstance(result, dict) else (
        result if isinstance(result, str) else None
    )
    return SubmitResult(attempt_id=attempt_id, state=state)
