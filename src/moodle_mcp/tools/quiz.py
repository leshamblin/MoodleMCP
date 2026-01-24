"""
Quiz tools - READ and WRITE operations for quizzes and attempts.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, resolve_user_id
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

# ============================================================================
# READ OPERATIONS
# ============================================================================

@mcp.tool(
    name="moodle_get_quizzes",
    description="Get all quizzes in a course. REQUIRED: course_id (integer). Example: course_id=7299. Returns quiz IDs, names, and details.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_quizzes(
    course_id: int = Field(description="Course ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of quizzes in a course.

    Returns all quizzes with their details including time limits,
    attempts allowed, and grading methods.

    Args:
        course_id: Course ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of quizzes with details

    Example use cases:
        - "What quizzes are in course 7299?"
        - "List all quizzes in my course"
        - "Show quiz details for course 7299"
    """
    moodle = get_moodle_client(ctx)

    try:
        quizzes_data = await moodle._make_request(
            'mod_quiz_get_quizzes_by_courses',
            {'courseids[0]': course_id}
        )

        quizzes = quizzes_data.get('quizzes', [])

        if not quizzes:
            return f"No quizzes found in course {course_id}."

        return format_response(quizzes, f"Quizzes in Course {course_id}", format)
    except Exception as e:
        return f"Unable to retrieve quizzes for course {course_id}. Error: {str(e)}"

@mcp.tool(
    name="moodle_get_quiz_attempts",
    description="Get user's attempts for a quiz. REQUIRED: quiz_id (integer). Optional: user_id (integer, omit for current user). Example: quiz_id=456. Returns attempt details including status, grades, and timestamps.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_quiz_attempts(
    quiz_id: int = Field(description="Quiz ID", gt=0),
    user_id: int | None = Field(None, description="User ID (omit for current user)"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get user's quiz attempts.

    Shows all attempts with their status (in progress, finished),
    grades, and timing information.

    Args:
        quiz_id: Quiz ID
        user_id: User ID (None for current user)
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of quiz attempts

    Example use cases:
        - "Show my attempts for quiz 456"
        - "Get quiz attempt history"
        - "What attempts does user 123 have for quiz 456?"
    """
    moodle = get_moodle_client(ctx)

    # Resolve user_id (defaults to current user if None)
    user_id = await resolve_user_id(moodle, user_id)

    try:
        params = {'quizid': quiz_id}
        if user_id:
            params['userid'] = user_id

        attempts_data = await moodle._make_request(
            'mod_quiz_get_user_attempts',
            params
        )

        attempts = attempts_data.get('attempts', [])

        if not attempts:
            return f"No attempts found for quiz {quiz_id}."

        return format_response(attempts, f"Quiz Attempts (Quiz {quiz_id})", format)
    except Exception as e:
        return f"Unable to retrieve quiz attempts. Error: {str(e)}"

# ============================================================================
# WRITE OPERATIONS - Require write permission for quiz attempts
# ============================================================================

@mcp.tool(
    name="moodle_start_quiz_attempt",
    description="Start a new quiz attempt. REQUIRED: course_id (integer), quiz_id (integer). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, quiz_id=456. Returns attempt ID to use for saving answers.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,  # Creates new attempt each time
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_start_quiz_attempt(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    quiz_id: int = Field(description="Quiz ID to start", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Start a new quiz attempt.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Creates a new attempt and returns the attempt ID needed for
    saving answers and submitting the quiz.

    Args:
        course_id: Course ID (must be in whitelist!)
        quiz_id: Quiz ID to start
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Attempt details including attempt ID

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Start quiz 456 in course 7299"
        - "Begin a new attempt for quiz 789"
        - "Start the practice quiz"
    """
    moodle = get_moodle_client(ctx)

    try:
        result = await moodle._make_request(
            'mod_quiz_start_attempt',
            {'quizid': quiz_id}
        )

        attempt = result.get('attempt', {})
        attempt_id = attempt.get('id')

        if not attempt_id:
            return "Quiz attempt started but no ID returned. Check your quiz attempts."

        response_data = {
            'attempt_id': attempt_id,
            'quiz_id': quiz_id,
            'course_id': course_id,
            'state': attempt.get('state', 'inprogress')
        }

        return format_response(response_data, "Quiz Attempt Started", format)
    except Exception as e:
        raise Exception(f"Failed to start quiz attempt: {str(e)}")

@mcp.tool(
    name="moodle_save_quiz_answers",
    description="Save answers during a quiz attempt (auto-save). REQUIRED: course_id (integer), attempt_id (integer), answers (array of objects with slot and answer). WRITE OPERATION - only works on whitelisted courses. Example: course_id=7299, attempt_id=123, answers=[{'slot':1,'answer':'42'}]. Use this periodically while taking quiz.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,  # Safe to save same answers multiple times
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_save_quiz_answers(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    attempt_id: int = Field(description="Attempt ID from start_quiz_attempt", gt=0),
    answers: list[dict] = Field(description="List of {slot: int, answer: str} objects", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Save quiz answers during an attempt (auto-save feature).

    SAFETY: This write operation is only allowed on whitelisted courses.

    This is the auto-save function that saves answers periodically
    without submitting the quiz. Answers can be changed later.

    Args:
        course_id: Course ID (must be in whitelist!)
        attempt_id: Attempt ID from moodle_start_quiz_attempt
        answers: List of {slot: int, answer: str} dictionaries
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation of saved answers

    Example use cases:
        - "Save answer '42' for question slot 1"
        - "Auto-save my quiz progress"
        - "Save answers for slots 1, 2, and 3"
    """
    moodle = get_moodle_client(ctx)

    # Build answer data
    params = {'attemptid': attempt_id}
    for idx, answer_data in enumerate(answers):
        slot = answer_data.get('slot')
        answer = answer_data.get('answer')
        params[f'data[{idx}][name]'] = f'q{slot}:answer'
        params[f'data[{idx}][value]'] = str(answer)

    try:
        result = await moodle._make_request(
            'mod_quiz_save_attempt',
            params
        )

        response_data = {
            'attempt_id': attempt_id,
            'course_id': course_id,
            'answers_saved': len(answers),
            'status': 'saved'
        }

        return format_response(response_data, "Quiz Answers Saved", format)
    except Exception as e:
        raise Exception(f"Failed to save quiz answers: {str(e)}")

@mcp.tool(
    name="moodle_submit_quiz",
    description="Submit a quiz attempt for grading (final submit). REQUIRED: course_id (integer), attempt_id (integer). WRITE OPERATION - FINAL ACTION - only works on whitelisted courses. Example: course_id=7299, attempt_id=123. This submits the quiz for grading and cannot be undone.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,  # Final submission, cannot undo
        "idempotentHint": True,   # Safe to submit multiple times (no effect after first)
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_submit_quiz(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    attempt_id: int = Field(description="Attempt ID to submit", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Submit quiz attempt for final grading.

    SAFETY: This write operation is only allowed on whitelisted courses.

    WARNING: This is a FINAL action. Once submitted, the attempt cannot
    be reopened or modified (unless the quiz allows review/editing).

    Args:
        course_id: Course ID (must be in whitelist!)
        attempt_id: Attempt ID to submit
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Submission confirmation with final grade

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Submit quiz attempt 123"
        - "Finish and submit my quiz"
        - "Final submit for quiz attempt"
    """
    moodle = get_moodle_client(ctx)

    try:
        params = {
            'attemptid': attempt_id,
            'timeup': 0,  # Not a timeout submission
            'finishattempt': 1  # Explicitly finish
        }

        result = await moodle._make_request(
            'mod_quiz_process_attempt',
            params
        )

        response_data = {
            'attempt_id': attempt_id,
            'course_id': course_id,
            'status': 'submitted'
        }

        return format_response(response_data, "Quiz Submitted", format)
    except Exception as e:
        raise Exception(f"Failed to submit quiz: {str(e)}")
