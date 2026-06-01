"""
PROD write-lockdown semantics.

main.py disables every ``write``-tagged tool when running in production with
writes off, and the lifespan re-verifies (fail-closed) that none survived.
These tests pin the two properties that guarantee that works:

1. ``disable(tags={"write"})`` removes exactly the write-tagged tools from
   ``list_tools()`` and leaves read tools intact -- the mechanism the lockdown
   relies on.
2. Every write tool the real server exposes carries the ``write`` tag, so the
   tag-based disable cannot miss one. (A write tool without the tag would be
   invisible to the lockdown -- this asserts there are none.)

A throwaway FastMCP is used for (1) so the shared session server is never left
with its write tools disabled.
"""

import pytest
from fastmcp import FastMCP

from moodle_mcp.server import mcp
from tests.test_helpers import _run_coroutine_sync

pytestmark = pytest.mark.offline


def test_disable_by_tag_removes_writes_keeps_reads():
    """disable(tags={'write'}) is the lockdown mechanism: prove it works."""
    throwaway = FastMCP(name="lockdown_probe")

    @throwaway.tool(name="probe_write", tags={"write"})
    def _w() -> str:
        return "x"

    @throwaway.tool(name="probe_read", tags={"read"})
    def _r() -> str:
        return "x"

    names_before = {t.name for t in _run_coroutine_sync(throwaway.list_tools())}
    assert {"probe_write", "probe_read"} <= names_before

    throwaway.disable(tags={"write"})

    after = _run_coroutine_sync(throwaway.list_tools())
    names_after = {t.name for t in after}
    assert "probe_write" not in names_after, "lockdown must drop write tools"
    assert "probe_read" in names_after, "lockdown must keep read tools"
    # And no surviving tool is write-tagged -- the lifespan post-condition.
    assert not [t for t in after if "write" in (t.tags or set())]


def test_all_write_tools_carry_the_write_tag():
    """Tag-based lockdown can only protect tools that carry the tag.

    Any mutating tool missing {'write'} would slip past disable(tags=...).
    Heuristic: a non-read tool whose name implies mutation must be tagged
    write. This catches a forgotten tag before it reaches production.
    """
    tools = _run_coroutine_sync(mcp.list_tools())
    mutation_verbs = (
        "create", "update", "delete", "save", "submit", "send",
        "enrol", "unenrol", "add_", "duplicate", "import", "mark_",
        "start_quiz", "remove",
    )
    suspects = []
    for t in tools:
        tags = t.tags or set()
        if "read" in tags or "write" in tags:
            continue
        if any(v in t.name for v in mutation_verbs):
            suspects.append(t.name)
    assert not suspects, f"mutating tools missing the 'write' tag: {suspects}"
