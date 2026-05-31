"""
Offline unit tests for MoodleResolver.

A fake client records calls and returns canned payloads, so the resolution
logic (int passthrough, email vs username, shortname->idnumber fallback,
activity name->ids, ambiguity/not-found, per-call memoization) is verified
with no network.
"""

import pytest

from moodle_mcp.core.resolvers import MoodleResolver, ActivityIds
from moodle_mcp.core.exceptions import (
    AmbiguousIdentifierError,
    IdentifierNotFoundError,
)

pytestmark = pytest.mark.offline


class FakeClient:
    """Records (function, params) calls and returns queued responses."""

    def __init__(self, responses: dict):
        # responses: function_name -> list of payloads (popped in order) OR a single payload
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []
        self.site_info_calls = 0

    async def call(self, function_name, params=None):
        self.calls.append((function_name, params or {}))
        resp = self.responses.get(function_name)
        if isinstance(resp, list):
            return resp.pop(0)
        return resp

    async def get_site_info(self):
        self.site_info_calls += 1
        return {"userid": 999}

    def count(self, function_name):
        return sum(1 for fn, _ in self.calls if fn == function_name)


# ---------------------------------------------------------------------- users
async def test_user_id_int_passthrough():
    r = MoodleResolver(FakeClient({}))
    assert await r.user_id(624) == 624


async def test_user_id_none_is_current_user():
    fake = FakeClient({})
    r = MoodleResolver(fake)
    assert await r.user_id(None) == 999
    # memoized: second call does not hit site info again
    assert await r.user_id(None) == 999
    assert fake.site_info_calls == 1


async def test_user_id_email_branch():
    fake = FakeClient({"core_user_get_users_by_field": [[{"id": 12, "fullname": "A"}]]})
    r = MoodleResolver(fake)
    assert await r.user_id("a@x.edu") == 12
    fn, params = fake.calls[0]
    assert fn == "core_user_get_users_by_field"
    assert params == {"field": "email", "values": ["a@x.edu"]}


async def test_user_id_username_then_email_fallback():
    # username lookup returns empty, email lookup returns a hit
    fake = FakeClient(
        {"core_user_get_users_by_field": [[], [{"id": 7, "fullname": "B"}]]}
    )
    r = MoodleResolver(fake)
    assert await r.user_id("bsmith") == 7
    assert [p["field"] for _, p in fake.calls] == ["username", "email"]


async def test_user_id_not_found():
    fake = FakeClient({"core_user_get_users_by_field": [[], []]})
    r = MoodleResolver(fake)
    with pytest.raises(IdentifierNotFoundError):
        await r.user_id("ghost")


async def test_user_id_ambiguous():
    fake = FakeClient(
        {"core_user_get_users_by_field": [[{"id": 1, "fullname": "X"}, {"id": 2, "fullname": "Y"}]]}
    )
    r = MoodleResolver(fake)
    with pytest.raises(AmbiguousIdentifierError):
        await r.user_id("a@x.edu")


async def test_user_id_memoized():
    fake = FakeClient({"core_user_get_users_by_field": [[{"id": 5, "fullname": "Z"}]]})
    r = MoodleResolver(fake)
    await r.user_id("z@x.edu")
    await r.user_id("z@x.edu")
    assert fake.count("core_user_get_users_by_field") == 1


# --------------------------------------------------------------------- courses
async def test_course_id_int_passthrough():
    r = MoodleResolver(FakeClient({}))
    assert await r.course_id(7299) == 7299


async def test_course_id_shortname():
    fake = FakeClient(
        {"core_course_get_courses_by_field": [{"courses": [{"id": 7299, "shortname": "PLAY"}]}]}
    )
    r = MoodleResolver(fake)
    assert await r.course_id("PLAY") == 7299
    _, params = fake.calls[0]
    assert params == {"field": "shortname", "value": "PLAY"}


async def test_course_id_idnumber_fallback():
    fake = FakeClient(
        {
            "core_course_get_courses_by_field": [
                {"courses": []},
                {"courses": [{"id": 800, "shortname": "S"}]},
            ]
        }
    )
    r = MoodleResolver(fake)
    assert await r.course_id("IDNUM-1") == 800
    assert [p["field"] for _, p in fake.calls] == ["shortname", "idnumber"]


async def test_course_id_not_found():
    fake = FakeClient(
        {"core_course_get_courses_by_field": [{"courses": []}, {"courses": []}]}
    )
    r = MoodleResolver(fake)
    with pytest.raises(IdentifierNotFoundError):
        await r.course_id("nope")


# ------------------------------------------------------------------ activities
CONTENTS = [
    {
        "modules": [
            {"id": 101, "instance": 11, "modname": "assign", "name": "Essay 1"},
            {"id": 102, "instance": 22, "modname": "quiz", "name": "Quiz 1"},
            {"id": 103, "instance": 33, "modname": "forum", "name": "Essay 1"},
        ]
    }
]


async def test_activity_by_name_with_modname():
    fake = FakeClient({"core_course_get_contents": [CONTENTS]})
    r = MoodleResolver(fake)
    act = await r.activity(7299, "Essay 1", modname="assign")
    assert isinstance(act, ActivityIds)
    assert act.cmid == 101 and act.instance == 11 and act.modname == "assign"


async def test_activity_by_cmid():
    fake = FakeClient({"core_course_get_contents": [CONTENTS]})
    r = MoodleResolver(fake)
    act = await r.activity(7299, 102)
    assert act.instance == 22 and act.modname == "quiz"


async def test_activity_ambiguous_name_without_modname():
    # "Essay 1" exists as both assign and forum
    fake = FakeClient({"core_course_get_contents": [CONTENTS]})
    r = MoodleResolver(fake)
    with pytest.raises(AmbiguousIdentifierError):
        await r.activity(7299, "Essay 1")


async def test_activity_not_found():
    fake = FakeClient({"core_course_get_contents": [CONTENTS]})
    r = MoodleResolver(fake)
    with pytest.raises(IdentifierNotFoundError):
        await r.activity(7299, "Nonexistent")


async def test_activity_contents_cached():
    fake = FakeClient({"core_course_get_contents": [CONTENTS]})
    r = MoodleResolver(fake)
    await r.activity(7299, 101)
    await r.activity(7299, 102)
    assert fake.count("core_course_get_contents") == 1
