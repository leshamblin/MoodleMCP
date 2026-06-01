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
    assert res.total >= 1


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


async def test_assignment_details_by_name(all_tools, ctx):
    """Ergonomics: resolve an assignment by NAME + course (no id lookup)."""
    listed = await tool(all_tools, "moodle_list_assignments")(course=COURSE, ctx=ctx)
    if listed.count == 0:
        pytest.skip("course 7299 has no assignments to resolve by name")
    name = listed.assignments[0].name
    details = await tool(all_tools, "moodle_get_assignment_details")(
        course=COURSE, assignment=name, ctx=ctx
    )
    assert details.name == name
    assert details.id > 0


async def test_save_grade_by_name(all_tools, ctx, moodle_client):
    """Ergonomics + write: grade a real enrolled user by assignment NAME.

    The assignment and the user are both discovered from course 7299, so no
    ids are hard-coded. The student's prior grade is captured and restored in
    a finally, so this never permanently alters a real grade even if an
    assertion fails.
    """
    listed = await tool(all_tools, "moodle_list_assignments")(course=COURSE, ctx=ctx)
    if listed.count == 0:
        pytest.skip("course 7299 has no assignments")
    assignment_name = listed.assignments[0].name
    assignment_instance = listed.assignments[0].id

    enrolled = await tool(all_tools, "moodle_get_enrolled_users")(course=COURSE, ctx=ctx)
    if not enrolled.users:
        pytest.skip("course 7299 has no enrolled users")
    students = [u for u in enrolled.users if "student" in (u.roles or [])]
    target = (students or enrolled.users)[0]

    # Capture the student's current grade so we can restore it afterwards.
    # Moodle has no "ungrade", so an empty prior grade is restored as -1
    # (its "no grade" sentinel).
    prior = await _current_assign_grade(moodle_client, assignment_instance, target.id)

    try:
        result = await tool(all_tools, "moodle_save_assignment_grade")(
            course=COURSE, assignment=assignment_name, user=target.id,
            grade=85.0, feedback="auto-test", ctx=ctx,
        )
        assert result.user_id == target.id
        assert result.grade == 85.0
        assert result.feedback_saved is True
    finally:
        await tool(all_tools, "moodle_save_assignment_grade")(
            course=COURSE, assignment=assignment_name, user=target.id,
            grade=prior if prior is not None else -1, feedback="", ctx=ctx,
        )


async def _current_assign_grade(client, assignment_instance: int, user_id: int):
    """Return the student's current numeric grade for an assignment, or None."""
    data = await client.call(
        "mod_assign_get_grades", {"assignmentids": [assignment_instance]}
    )
    for a in (data or {}).get("assignments", []):
        for g in a.get("grades", []):
            if g.get("userid") == user_id:
                try:
                    val = float(g.get("grade"))
                except (TypeError, ValueError):
                    return None
                return val if val >= 0 else None
    return None


async def test_student_overview_one_call(all_tools, ctx):
    """One aggregate call returns courses (+ events/grades) without chaining."""
    res = await tool(all_tools, "moodle_get_student_overview")(ctx=ctx)
    assert res.user_id > 0
    assert res.course_count == len(res.courses)
    assert res.course_count >= 1
    assert isinstance(res.upcoming_events, list)
    assert isinstance(res.recent_grades, list)


# --------------------------------------------------------------------- calendar
async def test_upcoming_events(all_tools, ctx):
    res = await tool(all_tools, "moodle_get_calendar_events")(sort_by_time=True, ctx=ctx)
    assert hasattr(res, "events")


async def test_calendar_create_delete(all_tools, ctx):
    """Reversible write: create a course event, then delete it.

    The delete runs in a finally so a failed assertion can never leak the
    event onto the live calendar.
    """
    created = await tool(all_tools, "moodle_create_calendar_event")(
        course=COURSE, event_name="_pytest_event",
        event_time=1893456000, description="temp", duration=0, ctx=ctx,
    )
    try:
        assert created.event_id > 0
    finally:
        deleted = await tool(all_tools, "moodle_delete_calendar_event")(
            course=COURSE, event_id=created.event_id, repeat=False, ctx=ctx,
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
        ("moodle_enrol_users", {"course": BLOCKED_COURSE, "users": [1], "role_id": 5}),
        ("moodle_unenrol_users", {"course": BLOCKED_COURSE, "users": [1]}),
        ("moodle_create_groups", {"course": BLOCKED_COURSE, "name": "x"}),
        ("moodle_create_calendar_event", {"course": BLOCKED_COURSE, "event_name": "x", "event_time": 1893456000}),
        ("moodle_save_assignment_grade", {"course": BLOCKED_COURSE, "assignment": 1, "user": 1, "grade": 50}),
        ("moodle_start_quiz_attempt", {"course": BLOCKED_COURSE, "quiz": 1}),
        ("moodle_create_forum_discussion", {"course": BLOCKED_COURSE, "forum_id": 1, "subject": "x", "message": "y"}),
        ("moodle_add_group_members", {"course": BLOCKED_COURSE, "group_id": 1, "user": 1}),
        ("moodle_delete_groups", {"course": BLOCKED_COURSE, "group_id": 1}),
        ("moodle_delete_course", {"course": BLOCKED_COURSE}),
    ],
)
async def test_write_safety_blocks_non_whitelisted_course(all_tools, ctx, name, kwargs):
    """Every course-scoped write must refuse a non-whitelisted course."""
    with pytest.raises((WriteOperationError, ToolError)):
        await tool(all_tools, name)(ctx=ctx, **kwargs)
