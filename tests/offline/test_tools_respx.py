"""
Offline tool-level tests: drive whole tool bodies with mocked Moodle HTTP.

Unlike test_make_request.py (which exercises the client) and test_resolvers.py
(the resolver), these run a *tool function* end to end -- ref resolution, param
assembly, the Moodle call(s), and the dataclass mapping -- without a live server
or credentials. A respx router dispatches on the POSTed ``wsfunction`` so one
fixture can serve the several functions a single tool calls.

This gives CI real tool coverage when no token is present (the live suites are
skipped there). Each test asserts both the OUTGOING request shape (the tool
sent the right function with the right params) and the RETURNED dataclass.
"""

from urllib.parse import parse_qsl

import httpx
import pytest
import respx

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import MoodleConfig
from moodle_mcp.server import mcp
from tests.test_helpers import MockContext, get_tool_by_name

pytestmark = pytest.mark.offline

ENDPOINT = "https://example.invalid/webservice/rest/server.php"


def _client() -> MoodleAPIClient:
    return MoodleAPIClient(base_url="https://example.invalid", token="tok")


def _config() -> MoodleConfig:
    return MoodleConfig(
        env="dev",
        dev_url="https://example.invalid",
        dev_token="tok",
        dev_course_whitelist="7299",
    )


class Router:
    """Dispatch each POST to a per-wsfunction handler; record the calls."""

    def __init__(self, handlers: dict):
        self.handlers = handlers
        self.calls: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        form = dict(parse_qsl(request.content.decode()))
        fn = form.get("wsfunction", "")
        self.calls.append(form)
        body = self.handlers.get(fn)
        if body is None:
            # Unmocked function -> empty/neutral success so tools don't crash;
            # tests assert on the functions they care about explicitly.
            return httpx.Response(200, json=[])
        if callable(body):
            body = body(form)
        return httpx.Response(200, json=body)

    def form_for(self, fn: str) -> dict:
        return next(f for f in self.calls if f.get("wsfunction") == fn)


def _mount(router: Router):
    respx.post(ENDPOINT).mock(side_effect=router)


@respx.mock
async def test_get_calendar_events_passes_courseids_and_maps_events():
    """Reader must send events[courseids][] and return mapped CalendarEvent rows."""
    router = Router({
        # resolver.user_id(None) -> current user via site info
        "core_webservice_get_site_info": {"userid": 100},
        # current user's enrolled courses (no 'course' arg -> aggregate path)
        "core_enrol_get_users_courses": [{"id": 7299}, {"id": 8001}],
        "core_calendar_get_calendar_events": {
            "events": [
                {"id": 1, "name": "Lab due", "eventtype": "due",
                 "courseid": 7299, "timestart": 1700000000, "timeduration": 0},
            ],
            "warnings": [],
        },
    })
    _mount(router)

    ctx = MockContext(_client(), config=_config())
    fn = get_tool_by_name(mcp, "moodle_get_calendar_events")
    result = await fn(days_ahead=30, ctx=ctx)

    # Outgoing: the enrolled course ids were sent as events[courseids][i].
    cal = router.form_for("core_calendar_get_calendar_events")
    assert cal["events[courseids][0]"] == "7299"
    assert cal["events[courseids][1]"] == "8001"
    assert cal["options[userevents]"] == "1"
    assert cal["options[siteevents]"] == "1"

    # Returned: one mapped event with the right fields.
    assert result.count == 1
    assert result.events[0].name == "Lab due"
    assert result.events[0].eventtype == "due"
    assert result.events[0].courseid == 7299


@respx.mock
async def test_save_assignment_grade_resolves_and_builds_plugindata():
    """Write tool must resolve name->instance, send nested plugindata, return result."""
    router = Router({
        # activity resolution: course contents -> module 'Lab Report 1'
        "core_course_get_contents": [
            {"modules": [
                {"id": 555, "instance": 42, "modname": "assign",
                 "name": "Lab Report 1"},
            ]},
        ],
        # user resolution by email
        "core_user_get_users_by_field": [{"id": 624, "fullname": "Stu Dent"}],
        # the grade save returns null on success
        "mod_assign_save_grade": None,
    })
    _mount(router)

    ctx = MockContext(_client(), config=_config())
    fn = get_tool_by_name(mcp, "moodle_save_assignment_grade")
    result = await fn(
        course=7299,
        assignment="Lab Report 1",
        user="stu@dent.edu",
        grade=92.0,
        feedback="Great work",
        ctx=ctx,
    )

    # Outgoing: assignmentid is the INSTANCE (42), not the cmid (555), and the
    # feedback rode in the nested plugindata editor.
    save = router.form_for("mod_assign_save_grade")
    assert save["assignmentid"] == "42"
    assert save["userid"] == "624"
    assert save["grade"] == "92.0"
    assert save["plugindata[assignfeedbackcomments_editor][text]"] == "Great work"
    assert save["plugindata[assignfeedbackcomments_editor][format]"] == "1"

    # Returned: the typed result reflects instance + feedback.
    assert result.assignment_id == 42
    assert result.user_id == 624
    assert result.feedback_saved is True


@respx.mock
async def test_get_forum_discussions_maps_and_flags_no_truncation():
    """Multi-step reader: forums -> discussions, mapped, truncated=False on a small course."""
    router = Router({
        "core_course_get_courses_by_field": {"courses": [{"id": 7299}]},
        "mod_forum_get_forums_by_courses": [
            {"id": 73600, "name": "General"},
        ],
        "mod_forum_get_forum_discussions": {
            "discussions": [
                {"discussion": 99, "name": "Welcome", "subject": "Welcome",
                 "userfullname": "Teacher", "numreplies": 2},
            ],
        },
    })
    _mount(router)

    ctx = MockContext(_client(), config=_config())
    fn = get_tool_by_name(mcp, "moodle_get_forum_discussions")
    result = await fn(course=7299, ctx=ctx)

    assert result.course_id == 7299
    assert result.count == 1
    assert result.discussions[0].id == 99
    assert result.discussions[0].forum_name == "General"
    assert result.truncated is False
