"""
Offline unit tests for MoodleAPIClient._flatten_params.

Phase 0 baseline: these tests document the CURRENT behavior of the flattener,
including the known nested-dict bug (captured as xfail). Phase 1 replaces the
flattener with a correct leaf-only encoder and flips the xfail to a pass.

No network access; the client is constructed directly with a dummy URL/token.
"""

import pytest

from moodle_mcp.core.client import MoodleAPIClient

pytestmark = pytest.mark.offline


@pytest.fixture
def client():
    """A client instance used only for its (pure) _flatten_params method."""
    return MoodleAPIClient(base_url="https://example.invalid", token="x")


def test_flatten_top_level_scalars(client):
    assert client._flatten_params({"courseid": 7299}) == {"courseid": "7299"}


def test_flatten_list_of_dicts(client):
    """Enrollment shape: list of objects -> bracketed leaf keys."""
    params = {"enrolments": [{"roleid": 5, "userid": 624, "courseid": 7299}]}
    assert client._flatten_params(params) == {
        "enrolments[0][roleid]": "5",
        "enrolments[0][userid]": "624",
        "enrolments[0][courseid]": "7299",
    }


def test_flatten_list_of_scalars(client):
    params = {"courseids": [1, 2, 3]}
    assert client._flatten_params(params) == {
        "courseids[0]": "1",
        "courseids[1]": "2",
        "courseids[2]": "3",
    }


def test_flatten_already_bracketed_string_keys_passthrough(client):
    """
    Legacy tools pre-flatten to bracket-string keys and pass them through.
    The flattener must treat such a key as an opaque top-level scalar so those
    tools keep working until they are refactored (Phase 1 coexistence property).
    """
    params = {"events[0][name]": "Office Hours"}
    assert client._flatten_params(params) == {"events[0][name]": "Office Hours"}


def test_flatten_nested_dict_no_stray_keys(client):
    """
    Deep nesting (grading feedback plugindata). Only leaf scalars produce keys;
    no stray 'plugindata]'-style empty params.
    """
    params = {
        "assignmentid": 123,
        "plugindata": {"assignfeedbackcomments_editor": {"text": "Good work", "format": 1}},
    }
    assert client._flatten_params(params) == {
        "assignmentid": "123",
        "plugindata[assignfeedbackcomments_editor][text]": "Good work",
        "plugindata[assignfeedbackcomments_editor][format]": "1",
    }


def test_flatten_none_dropped_and_bool_as_int(client):
    params = {"keep": 1, "drop": None, "flag_true": True, "flag_false": False}
    assert client._flatten_params(params) == {
        "keep": "1",
        "flag_true": "1",
        "flag_false": "0",
    }


def test_flatten_options_name_value_list(client):
    """Quiz/forum 'options' shape: list of {name, value} objects."""
    params = {"attemptid": 99, "data": [{"name": "q1:answer", "value": "42"}]}
    assert client._flatten_params(params) == {
        "attemptid": "99",
        "data[0][name]": "q1:answer",
        "data[0][value]": "42",
    }
