"""
Lean live integration tests against the dev Moodle instance (course 7299).

These replace the older test_real_api.py / test_user_course_lookup.py, which
were coupled to the removed string/`format=` API. Here we call the real tools
via the `all_tools` fixture and assert on their typed dataclass fields. One
focused test per tool category; write tools are exercised reversibly (or only
their safety is checked) so the suite is safe to re-run.

The root conftest forces MOODLE_ENV=dev and whitelists course 7299.
"""

import pytest

from fastmcp.exceptions import ToolError
from moodle_mcp.utils.error_handling import WriteOperationError

COURSE = 7299
BLOCKED_COURSE = 99999


def tool(all_tools, name):
    fn = all_tools.get(name)
    assert fn is not None, f"tool {name} not registered"
    return fn


# ------------------------------------------------------------------ site / users
async def test_site_info(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_site_info")(ctx=ctx)
    assert res.userid > 0
    assert res.sitename
    assert res.function_count > 0


async def test_connection(all_tools, ctx):
    res = await tool(all_tools, "moodle_test_connection")(ctx=ctx)
    assert res.connected is True


async def test_available_functions(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_available_functions")(ctx=ctx)
    assert res.count > 10
    assert any(n.startswith("core_") for n in res.functions)


async def test_current_user(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_current_user")(ctx=ctx)
    assert res.id > 0


async def test_user_profile_by_id(all_tools, ctx, moodle_client):
    res = await tool(all_tools, "moodle_get_user_profile")(
        user=moodle_client.current_user_id, ctx=ctx
    )
    assert res.id == moodle_client.current_user_id


async def test_search_users_by_email(all_tools, ctx):
    """Resolve the authenticated user's own email so the test is deterministic."""
    me = await tool(all_tools, "moodle_get_current_user")(ctx=ctx)
    email = getattr(me, "email", None)
    res = await tool(all_tools, "moodle_search_users")(
        search_query=email or "nobody@example.invalid", ctx=ctx
    )
    assert hasattr(res, "users") and hasattr(res, "count")
    if email:
        assert res.count >= 1


async def test_invalid_user_id_raises(all_tools, ctx):
    with pytest.raises(ToolError):
        await tool(all_tools, "moodle_get_user_profile")(user=99999999, ctx=ctx)


# ----------------------------------------------------------------------- courses
async def test_list_user_courses(all_tools, ctx):
    res = await tool(all_tools, "moodle_list_user_courses")(ctx=ctx)
    assert res.count >= 1


async def test_list_user_courses_by_id(all_tools, ctx, moodle_client):
    res = await tool(all_tools, "moodle_list_user_courses")(
        user=moodle_client.current_user_id, ctx=ctx
    )
    assert res.count >= 1


async def test_include_hidden_courses(all_tools, ctx):
    visible = await tool(all_tools, "moodle_list_user_courses")(include_hidden=False, ctx=ctx)
    allc = await tool(all_tools, "moodle_list_user_courses")(include_hidden=True, ctx=ctx)
    assert allc.count >= visible.count


async def test_course_details_by_id(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_course_details")(course=COURSE, ctx=ctx)
    assert res.id == COURSE


async def test_course_details_by_shortname(all_tools, ctx):
    """Name-resolution: shortname -> id (the chaining-reduction feature)."""
    res = await tool(all_tools, "moodle_get_course_details")(course="MoodlePlayground", ctx=ctx)
    assert res.id == COURSE


async def test_course_contents(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_course_contents")(course=COURSE, ctx=ctx)
    assert res.count >= 1


async def test_enrolled_users(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_enrolled_users")(course=COURSE, ctx=ctx)
    assert res.count >= 1


async def test_course_categories(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_course_categories")(ctx=ctx)
    assert res.count >= 1


# ------------------------------------------------------------------------ groups
async def test_course_groups(all_tools, ctx):
    # Listing groups requires the manage-groups capability; some tokens lack it
    # on the test course. Accept a permission error as a valid (non-code)
    # outcome and otherwise assert the typed shape.
    try:
        res = await tool(all_tools, "moodle_get_course_groups")(course=COURSE, ctx=ctx)
    except ToolError as e:
        if "managegroups" in str(e) or "permission" in str(e).lower():
            pytest.skip("token lacks manage-groups capability on the test course")
        raise
    assert hasattr(res, "groups")


# ------------------------------------------------------------------------- quiz
async def test_get_quizzes(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_quizzes")(course=COURSE, ctx=ctx)
    assert hasattr(res, "quizzes")


# ------------------------------------------------------------------- assignments
async def test_list_assignments(all_tools, ctx):
    res = await tool(all_tools, "moodle_list_assignments")(course=COURSE, ctx=ctx)
    assert hasattr(res, "assignments")


# --------------------------------------------------------------------- calendar
async def test_upcoming_events(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_upcoming_events")(ctx=ctx)
    assert hasattr(res, "events")


async def test_calendar_create_delete(all_tools, ctx):
    """Reversible write: create a course event, then delete it."""
    created = await tool(all_tools, "moodle_create_calendar_event")(
        course_id=COURSE, event_name="_pytest_event",
        event_time=1893456000, description="temp", duration=0, ctx=ctx,
    )
    assert created.event_id > 0
    deleted = await tool(all_tools, "moodle_delete_calendar_event")(
        course_id=COURSE, event_id=created.event_id, repeat=False, ctx=ctx,
    )
    assert deleted.event_id == created.event_id


# --------------------------------------------------------------------- messages
async def test_unread_count(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_unread_count")(ctx=ctx)
    assert res.count >= 0


# -------------------------------------------------------------- write-safety
@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("moodle_enrol_users", {"course_id": BLOCKED_COURSE, "user_ids": [1], "role_id": 5}),
        ("moodle_unenrol_users", {"course_id": BLOCKED_COURSE, "user_ids": [1]}),
        ("moodle_create_groups", {"course_id": BLOCKED_COURSE, "groups": [{"name": "x"}]}),
        ("moodle_create_calendar_event", {"course_id": BLOCKED_COURSE, "event_name": "x", "event_time": 1893456000}),
        ("moodle_save_assignment_grade", {"course_id": BLOCKED_COURSE, "assignment_id": 1, "user_id": 1, "grade": 50}),
        ("moodle_start_quiz_attempt", {"course_id": BLOCKED_COURSE, "quiz_id": 1}),
        ("moodle_create_forum_discussion", {"course_id": BLOCKED_COURSE, "forum_id": 1, "subject": "x", "message": "y"}),
    ],
)
async def test_write_safety_blocks_non_whitelisted_course(all_tools, ctx, name, kwargs):
    """Every course-scoped write must refuse a non-whitelisted course."""
    with pytest.raises((WriteOperationError, ToolError)):
        await tool(all_tools, name)(ctx=ctx, **kwargs)
