"""
Offline write-safety tests.

These exercise the write-permission decorators without touching the network:
- course writes are gated by the per-course whitelist
  (``require_write_permission`` -> ``config.can_write_to_course``)
- course-independent writes (messaging) are gated by the global write policy
  (``require_global_write_permission`` -> ``config.can_write_globally``)

The decorators run before the wrapped function body, so they raise before any
Moodle call is attempted; the client is never actually used.
"""

import pytest

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import MoodleConfig
from moodle_mcp.server import mcp
from moodle_mcp.utils.error_handling import WriteOperationError
from tests.test_helpers import MockContext, get_tool_by_name


def _client() -> MoodleAPIClient:
    # A real client object is fine; the decorators block before it is called.
    return MoodleAPIClient(base_url="https://example.invalid", token="x")


def _config(**overrides) -> MoodleConfig:
    base = dict(
        env="dev",
        dev_url="https://example.invalid",
        dev_token="x",
        dev_course_whitelist="7299",
    )
    base.update(overrides)
    return MoodleConfig(**base)


@pytest.mark.offline
async def test_send_message_blocked_when_global_writes_disabled():
    """moodle_send_message must refuse when dev_allow_global_writes is False."""
    ctx = MockContext(_client(), config=_config(dev_allow_global_writes=False))
    send = get_tool_by_name(mcp, "moodle_send_message")
    with pytest.raises(WriteOperationError):
        await send(recipient_user_id=123, message_text="hi", ctx=ctx)


@pytest.mark.offline
async def test_delete_conversation_blocked_when_global_writes_disabled():
    """moodle_delete_conversation must refuse when global writes are disabled."""
    ctx = MockContext(_client(), config=_config(dev_allow_global_writes=False))
    delete = get_tool_by_name(mcp, "moodle_delete_conversation")
    with pytest.raises(WriteOperationError):
        await delete(conversation_id=789, ctx=ctx)


@pytest.mark.offline
async def test_global_writes_blocked_in_prod_without_allow():
    """In PROD, global writes are blocked unless prod_allow_writes is True."""
    ctx = MockContext(
        _client(),
        config=_config(env="prod", prod_url="https://p.invalid",
                       prod_token="x", prod_allow_writes=False),
    )
    send = get_tool_by_name(mcp, "moodle_send_message")
    with pytest.raises(WriteOperationError):
        await send(recipient_user_id=123, message_text="hi", ctx=ctx)


@pytest.mark.offline
async def test_course_write_blocked_for_non_whitelisted_course():
    """A grade save on a non-whitelisted course must be blocked."""
    ctx = MockContext(_client(), config=_config())
    save = get_tool_by_name(mcp, "moodle_save_assignment_grade")
    with pytest.raises(WriteOperationError):
        # course 9999 is not in the whitelist; blocked before any API call.
        await save(course_id=9999, assignment_id=1, user_id=1, grade=50.0, ctx=ctx)
