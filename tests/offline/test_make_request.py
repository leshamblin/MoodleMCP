"""
Offline unit tests for MoodleAPIClient request handling using respx to mock httpx.

Covers:
- null-success: a function returning JSON ``null`` yields None (success).
- 200-error body: Moodle returns app errors as HTTP 200 with an exception body;
  the client must classify them into the right Moodle*Error subclass.
- outgoing encoding: nested params are sent as PHP-bracket form keys.
- raise_on_row_errors: per-row soft failures are detected.
"""

import httpx
import pytest
import respx

from moodle_mcp.core.client import MoodleAPIClient, raise_on_row_errors
from moodle_mcp.core.exceptions import (
    MoodleAPIError,
    MoodleAuthError,
    MoodleNotFoundError,
    MoodlePermissionError,
)

pytestmark = pytest.mark.offline

ENDPOINT = "https://example.invalid/webservice/rest/server.php"


@pytest.fixture
def client():
    return MoodleAPIClient(base_url="https://example.invalid", token="tok")


def _form(request) -> dict[str, str]:
    """Parse a form-encoded POST body into a dict of decoded keys/values."""
    from urllib.parse import parse_qsl

    body = request.content.decode()
    return dict(parse_qsl(body))


@respx.mock
async def test_null_success_returns_none(client):
    respx.post(ENDPOINT).mock(return_value=httpx.Response(200, text="null"))
    result = await client.call("enrol_manual_enrol_users",
                               {"enrolments": [{"roleid": 5, "userid": 1, "courseid": 7299}]})
    assert result is None
    await client.close()


@respx.mock
async def test_token_sent_in_body_not_url(client):
    """The auth token must travel in the POST body, never the URL query string."""
    route = respx.post(ENDPOINT).mock(return_value=httpx.Response(200, text="null"))
    await client.call("core_webservice_get_site_info", {})
    req = route.calls.last.request
    assert "wstoken" not in dict(req.url.params)  # not in the URL
    assert _form(req)["wstoken"] == "tok"          # in the body
    await client.close()


@respx.mock
async def test_outgoing_params_are_bracket_encoded(client):
    route = respx.post(ENDPOINT).mock(return_value=httpx.Response(200, text="null"))
    await client.call(
        "mod_assign_save_grade",
        {
            "assignmentid": 42,
            "userid": 624,
            "grade": 85.0,
            "plugindata": {"assignfeedbackcomments_editor": {"text": "Nice", "format": 1}},
        },
    )
    qs = _form(route.calls.last.request)
    assert qs["wsfunction"] == "mod_assign_save_grade"
    assert qs["moodlewsrestformat"] == "json"
    assert qs["assignmentid"] == "42"
    assert qs["plugindata[assignfeedbackcomments_editor][text]"] == "Nice"
    assert qs["plugindata[assignfeedbackcomments_editor][format]"] == "1"
    await client.close()


@respx.mock
@pytest.mark.parametrize(
    "errorcode,exc",
    [
        ("invalidtoken", MoodleAuthError),
        ("accessexception", MoodleAuthError),
        ("nopermission", MoodlePermissionError),
        ("invalidrecord", MoodleNotFoundError),
        ("somethingelse", MoodleAPIError),
    ],
)
async def test_200_error_body_classified(client, errorcode, exc):
    body = {
        "exception": "moodle_exception",
        "errorcode": errorcode,
        "message": "boom",
    }
    respx.post(ENDPOINT).mock(return_value=httpx.Response(200, json=body))
    with pytest.raises(exc):
        await client.call("core_course_get_courses", {})
    await client.close()


def test_raise_on_row_errors_message_send():
    rows = [
        {"msgid": 10, "errormessage": ""},
        {"msgid": -1, "errormessage": "Recipient is blocking messages"},
    ]
    with pytest.raises(MoodleAPIError) as ei:
        raise_on_row_errors(rows)
    assert "blocking" in str(ei.value)


def test_raise_on_row_errors_warnings_key():
    rows = [{"id": 1}, {"warnings": "bad event"}]
    with pytest.raises(MoodleAPIError):
        raise_on_row_errors(rows, error_keys=("warnings",))


def test_raise_on_row_errors_clean_passes():
    raise_on_row_errors([{"msgid": 1, "errormessage": ""}, {"msgid": 2}])
    raise_on_row_errors(None)  # non-list input ignored
