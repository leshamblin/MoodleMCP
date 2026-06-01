"""
Registry-driven write-safety test.

Rather than listing tools by hand (which lets a newly-added write tool ship
ungated and untested), this discovers EVERY ``write``-tagged tool from the
server and asserts each one refuses to run when writes are disabled.

Two gate types are covered, matched to how each tool is actually guarded:

- Course-scoped writes (have a ``course`` / ``course_id`` / ``*_course_id``
  parameter) are guarded by ``@require_write_permission`` and must block when
  invoked against a non-whitelisted course.
- Course-independent writes (no course parameter -- messaging, category and
  course creation/deletion) are guarded by ``@require_global_write_permission``
  and must block when global writes are disabled.

The config used here denies BOTH, so every write tool must block regardless of
which decorator it carries. The decorators run before the wrapped body, so they
raise before any network call -- the dummy arguments synthesised below never
reach Moodle (and the client points at an unroutable host as a backstop, so a
leak would surface as a *connection* error, not the safety error we assert on).

If this test fails for a tool, that tool is exposing an unguarded write.
"""

import inspect
import typing

import pytest
from fastmcp.exceptions import ToolError

from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import MoodleConfig
from moodle_mcp.server import mcp
from tests.test_helpers import MockContext, discover_tools, _run_coroutine_sync

pytestmark = pytest.mark.offline

# Parameter names that carry a course reference (-> require_write_permission).
COURSE_REF_PARAMS = {"course", "course_id", "source_course_id", "dest_course_id"}

# A course id that is NOT in the whitelist, so course-scoped writes block.
NON_WHITELISTED_COURSE = 9999


def _deny_all_config() -> MoodleConfig:
    """A config under which NO write of any kind is permitted."""
    return MoodleConfig(
        env="dev",
        dev_url="https://blackhole.invalid",
        dev_token="x",
        dev_course_whitelist="7299",      # 9999 is therefore blocked
        dev_allow_global_writes=False,    # global writes blocked too
    )


def _dummy_for(param: inspect.Parameter):
    """Synthesise a type-appropriate placeholder for a required parameter.

    Course-reference params get a non-whitelisted course id so the safety check
    triggers. Everything else gets a harmless value of the right shape -- these
    never reach the network because the gate raises first.
    """
    if param.name in COURSE_REF_PARAMS:
        return NON_WHITELISTED_COURSE

    ann = param.annotation
    origin = typing.get_origin(ann)
    if origin is not None:  # Annotated[...] / list[...] / X | None
        args = typing.get_args(ann)
        ann = args[0] if args else ann

    if ann in (int, float):
        return 1
    if ann is bool:
        return True
    if ann is str:
        return "x"
    if origin in (list, typing.List):
        return [1]
    if origin in (dict, typing.Dict):
        return {}
    # Fallback: an int satisfies most Moodle id-shaped params.
    return 1


def _required_kwargs(fn) -> dict:
    """Build kwargs covering every required (no-default) parameter except ctx."""
    sig = inspect.signature(fn)
    kwargs = {}
    for p in sig.parameters.values():
        if p.name == "ctx" or p.default is not inspect._empty:
            continue
        kwargs[p.name] = _dummy_for(p)
    return kwargs


def _write_tool_names() -> list[str]:
    tools = _run_coroutine_sync(mcp.list_tools())
    return sorted(t.name for t in tools if "write" in (t.tags or set()))


# An empty discovery would make a bare @parametrize SKIP silently (a vacuous
# pass). Substitute a sentinel so the test instead runs once and FAILS loudly,
# surfacing "discovery returned no write tools" rather than disappearing.
_WRITE_NAMES = _write_tool_names() or ["__NO_WRITE_TOOLS_DISCOVERED__"]


@pytest.mark.parametrize("tool_name", _WRITE_NAMES)
async def test_every_write_tool_blocks_when_writes_disabled(tool_name):
    """No write-tagged tool may execute when all writes are disabled."""
    assert tool_name != "__NO_WRITE_TOOLS_DISCOVERED__", (
        "registry discovery found zero write-tagged tools -- the tag-based "
        "lockdown and this safety net would both be silently inert"
    )
    ctx = MockContext(
        MoodleAPIClient(base_url="https://blackhole.invalid", token="x"),
        config=_deny_all_config(),
    )
    fn = discover_tools(mcp)[tool_name]
    kwargs = _required_kwargs(fn)

    with pytest.raises(ToolError, match="blocked for safety"):
        await fn(ctx=ctx, **kwargs)


def test_registry_found_all_write_tools():
    """Sanity: the discovery actually found the expected set of writes.

    Guards against a registry/tag regression silently shrinking coverage to a
    handful of tools and the parametrized test then 'passing' vacuously.
    """
    names = _write_tool_names()
    assert len(names) >= 28, f"expected >=28 write tools, found {len(names)}: {names}"
    # The three formerly-ungated admin tools must be present and covered.
    for n in (
        "moodle_create_course",
        "moodle_create_course_category",
        "moodle_delete_course_category",
    ):
        assert n in names
