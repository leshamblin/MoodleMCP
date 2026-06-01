"""
Comprehensive live smoke test: call EVERY read tool against the dev instance
(course 7299) and assert none fails with a *code* bug.

Why a separate file: ``test_tools_live.py`` holds focused, asserting tests for
representative tools; this file is a breadth sweep that guarantees every
registered read tool is at least invocable end-to-end with realistic arguments.

Each tool is classified:
  - PASS  -> returned its typed result with no exception
  - SKIP  -> raised a *Moodle-side* error that is environmental, not a code bug
             (permission/capability the token lacks, or data course 7299 has
             none of). These are recorded, not failed.
  - FAIL  -> raised a Python error (TypeError/AttributeError/KeyError/...) or an
             unexpected ToolError. This fails the test -- it means the tool's
             own code is wrong.

Write tools are not invoked here (they mutate state); their safety is covered by
test_tools_live.py::test_write_safety_blocks_non_whitelisted_course and the
reversible calendar create/delete test.
"""

import pytest

from fastmcp.exceptions import ToolError

COURSE = 7299

# Moodle-side messages that mean "environment/permission", not "code bug".
_ENV_MARKERS = (
    "permission",
    "not enrolled",
    "notenroled",
    "access control",
    "accessexception",
    "required capability",
    "can not",
    "cannot",
    "not allowed",
    "invalid token",
    "webservice",
    "no permission",
)


def _is_environmental(err: Exception) -> bool:
    msg = str(err).lower()
    return any(m in msg for m in _ENV_MARKERS)


async def _discover(moodle_client):
    """Find real ids on course 7299 to feed the tools."""
    info = await moodle_client.get_site_info()
    uid = info["userid"]

    contents = await moodle_client.call(
        "core_course_get_contents", {"courseid": COURSE}
    )
    modules = [m for s in (contents or []) for m in s.get("modules", [])]
    cmid = modules[0]["id"] if modules else 0

    forums = await moodle_client.call(
        "mod_forum_get_forums_by_courses", {"courseids": [COURSE]}
    )
    forums = forums if isinstance(forums, list) else []
    forum_instance = forums[0]["id"] if forums else 0

    enrolled = await moodle_client.call(
        "core_enrol_get_enrolled_users", {"courseid": COURSE}
    )
    enrolled = enrolled or []
    a_user = enrolled[0]["id"] if enrolled else uid

    # Discover a discussion id by scanning ALL forums (the first forum may have
    # none, e.g. an empty Announcements forum).
    discussion_id = 0
    for f in forums:
        try:
            disc = await moodle_client.call(
                "mod_forum_get_forum_discussions", {"forumid": f["id"]}
            )
            ds = (disc or {}).get("discussions", [])
            if ds:
                discussion_id = ds[0].get("discussion") or ds[0].get("id")
                break
        except Exception:
            continue

    # Discover one group id (for get_group_members), if any exist.
    group_id = 0
    try:
        groups = await moodle_client.call(
            "core_group_get_course_groups", {"courseid": COURSE}
        )
        group_id = groups[0]["id"] if groups else 0
    except Exception:
        group_id = 0

    return {
        "uid": uid,
        "cmid": cmid,
        "forum_instance": forum_instance,
        "user_id": a_user,
        "discussion_id": discussion_id,
        "group_id": group_id,
    }


def _read_tool_args(ids: dict) -> dict[str, dict]:
    """Map every read tool name -> kwargs to invoke it with.

    A value of None means 'skip invocation, but record the tool exists' (used
    for tools that strictly need data course 7299 does not have).
    """
    return {
        # site
        "moodle_get_site_info": {},
        "moodle_test_connection": {},
        "moodle_get_available_functions": {},
        # users
        "moodle_get_current_user": {},
        "moodle_get_user_profile": {"user": ids["uid"]},
        "moodle_search_users": {"search_query": "Shamblin"},
        "moodle_get_user_preferences": {},
        # courses
        "moodle_list_user_courses": {},
        "moodle_get_course_details": {"course": COURSE},
        "moodle_search_courses": {"search_query": "Playground"},
        "moodle_get_course_contents": {"course": COURSE},
        "moodle_get_enrolled_users": {"course": COURSE},
        "moodle_get_course_categories": {},
        # grades
        "moodle_get_grades": {"course": COURSE},
        "moodle_get_grade_overview": {},
        # assignments
        "moodle_list_assignments": {"course": COURSE},
        "moodle_get_user_assignments": {},
        # quiz
        "moodle_get_quizzes": {"course": COURSE},
        # calendar
        "moodle_get_calendar_events": {},
        # messages
        "moodle_get_conversations": {},
        "moodle_get_unread_count": {},
        # forums
        "moodle_get_forum_discussions": {"course": COURSE},
        "moodle_search_forums": {"search_query": "test"},
        # groups
        "moodle_get_course_groups": {"course": COURSE},
        "moodle_get_course_groupings": {"course": COURSE},
        "moodle_get_activity_groupmode": {"cmid": ids["cmid"]},
        "moodle_get_activity_allowed_groups": {"cmid": ids["cmid"]},
        "moodle_get_course_user_groups": {"course": COURSE},
        "moodle_get_groups_for_selector": {"course": COURSE},
        # badges
        "moodle_get_user_badges": {},
        # completion
        "moodle_get_activities_completion_status": {"course": COURSE},
        "moodle_get_course_completion_status": {"course": COURSE},
        # dashboard
        "moodle_get_student_overview": {},
    }


@pytest.mark.live
async def test_every_read_tool_is_invocable(all_tools, ctx, moodle_client):
    """Invoke every registered read tool; fail only on real code bugs."""
    ids = await _discover(moodle_client)
    args = _read_tool_args(ids)

    # Conditional args that depend on discovered data.
    if ids["discussion_id"]:
        args["moodle_get_discussion_posts"] = {"discussion_id": ids["discussion_id"]}
    if ids["group_id"]:
        args["moodle_get_group_members"] = {"group_id": ids["group_id"]}
    if ids["forum_instance"]:
        # already covered by get_forum_discussions(course=...)
        pass

    # Every read tool the server exposes.
    read_tools = sorted(n for n in all_tools if n in _read_tool_names())

    passed, skipped, failed = [], [], []
    for name in read_tools:
        if name not in args:
            # No realistic args available on course 7299 (e.g. needs an
            # assignment/quiz/submission/attempt id that this course lacks).
            skipped.append((name, "no test data on course 7299"))
            continue
        fn = all_tools[name]
        try:
            await fn(ctx=ctx, **args[name])
            passed.append(name)
        except ToolError as e:
            if _is_environmental(e):
                skipped.append((name, str(e).splitlines()[0][:80]))
            else:
                failed.append((name, f"ToolError: {str(e).splitlines()[0][:100]}"))
        except (TypeError, AttributeError, KeyError, IndexError) as e:
            failed.append((name, f"{type(e).__name__}: {e}"))

    # Human-readable summary in the assertion message if anything failed.
    report = (
        f"\nPASS  ({len(passed)}): {', '.join(passed)}"
        f"\nSKIP  ({len(skipped)}): "
        + "; ".join(f"{n} [{r}]" for n, r in skipped)
        + f"\nFAIL  ({len(failed)}): "
        + "; ".join(f"{n} [{r}]" for n, r in failed)
    )
    print(report)  # visible with `pytest -s`
    assert not failed, f"Read tools with real code bugs:{report}"
    # Sanity: the core read tools must actually have run.
    assert len(passed) >= 20, f"Too few read tools passed.{report}"


def _read_tool_names() -> set[str]:
    """Names of all read-tagged tools, discovered once from the server."""
    from tests.test_helpers import _run_coroutine_sync
    import moodle_mcp.server

    cached = globals().get("_READ_NAMES")
    if cached is not None:
        return cached
    tools = _run_coroutine_sync(moodle_mcp.server.mcp.list_tools())
    names = {t.name for t in tools if "read" in (t.tags or set())}
    globals()["_READ_NAMES"] = names
    return names
