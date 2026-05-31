"""
Live write-path test against the whitelisted dev course (7299).

Purpose: prove the corrected _flatten_params produces VALID Moodle params for
nested write operations (no invalidparameter errors), exercising the real
write tools end-to-end. Conservative and reversible where possible:

  - groups: create -> add member -> remove member -> delete (fully reversible)
  - calendar: create -> delete (fully reversible)
  - enrol: enrol an already-enrolled user (idempotent shape-probe)

The key assertion is that none of these produce a parameter-encoding error
(invalidparameter / "missing required key"); Moodle business/permission
errors are acceptable since they still prove the params were parsed.

Run:
  .venv/bin/python scripts/live_write_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Make both the package (src/) and the repo root (for tests.test_helpers)
# importable regardless of the working directory the script is launched from.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("MOODLE_ENV", "dev")

import moodle_mcp.main as _main  # noqa: F401  (registers tools, builds config)
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
from tests.test_helpers import MockContext

COURSE = 7299
results: list[tuple[str, str, str]] = []  # (name, status, detail)


def record(name, status, detail=""):
    results.append((name, status, detail))
    print(f"[{status}] {name}: {detail}")


def is_param_error(exc: Exception) -> bool:
    """True if the error looks like a parameter-encoding fault (our bug class)."""
    s = str(exc).lower()
    return "invalidparameter" in s or "invalid parameter" in s or "missing required key" in s


def fn(tool):
    return getattr(tool, "fn", tool)


async def main():
    cfg = get_config()
    print(f"ENV={cfg.environment_name} URL={cfg.url} whitelist={cfg._parsed_dev_whitelist}")
    if COURSE not in cfg._parsed_dev_whitelist:
        record("precondition", "SKIP", f"course {COURSE} not in whitelist {cfg._parsed_dev_whitelist}")
        return summarize()

    client = MoodleAPIClient(base_url=cfg.url, token=cfg.token, timeout=cfg.api_timeout)
    ctx = MockContext(client)

    from moodle_mcp.tools.groups import (
        moodle_create_groups, moodle_delete_groups,
        moodle_add_group_members, moodle_delete_group_members,
    )
    from moodle_mcp.tools.calendar import (
        moodle_create_calendar_event, moodle_delete_calendar_event,
    )
    from moodle_mcp.tools.enrollment import moodle_enrol_users

    info = await client.get_site_info()
    my_uid = info["userid"]

    # ---- 1. GROUP create -> add member -> remove member -> delete (reversible)
    group_id = None
    try:
        gname = f"_mcp_test_group_{my_uid}"
        await fn(moodle_create_groups)(
            course_id=COURSE,
            groups=[{"name": gname, "description": "temp group from live_write_test"}],
            ctx=ctx,
        )
        groups = await client.call("core_group_get_course_groups", {"courseid": COURSE})
        match = [g for g in (groups or []) if g.get("name") == gname]
        group_id = match[0]["id"] if match else None
        record("group.create", "PASS", f"id={group_id}")
    except Exception as e:
        record("group.create", "FAIL" if is_param_error(e) else "ERR",
               f"{type(e).__name__}: {str(e)[:120]}")

    if group_id:
        try:
            await fn(moodle_add_group_members)(
                course_id=COURSE, group_id=group_id, user_ids=[my_uid], ctx=ctx
            )
            record("group.add_member", "PASS", "added self")
        except Exception as e:
            record("group.add_member", "FAIL" if is_param_error(e) else "ERR",
                   f"{type(e).__name__}: {str(e)[:120]}")
        try:
            await fn(moodle_delete_group_members)(
                course_id=COURSE, group_id=group_id, user_ids=[my_uid], ctx=ctx
            )
            record("group.del_member", "PASS", "removed self")
        except Exception as e:
            record("group.del_member", "FAIL" if is_param_error(e) else "ERR",
                   f"{type(e).__name__}: {str(e)[:120]}")
        try:
            await fn(moodle_delete_groups)(course_id=COURSE, group_ids=[group_id], ctx=ctx)
            record("group.delete", "PASS", f"deleted id={group_id}")
        except Exception as e:
            record("group.delete", "FAIL" if is_param_error(e) else "ERR",
                   f"{type(e).__name__}: {str(e)[:120]}")

    # ---- 2. CALENDAR create -> delete (reversible)
    event_id = None
    try:
        when = 1893456000  # 2030-01-01, far future, harmless
        await fn(moodle_create_calendar_event)(
            course_id=COURSE, event_name="_mcp_test_event",
            event_time=when, description="temp", duration=0, ctx=ctx,
        )
        ev = await client.call("core_calendar_get_calendar_events", {
            "events": {"courseids": [COURSE]},
            "options": {"timestart": when - 86400, "timeend": when + 86400},
        })
        evs = (ev or {}).get("events", []) if isinstance(ev, dict) else []
        match = [e for e in evs if e.get("name") == "_mcp_test_event"]
        event_id = match[0]["id"] if match else None
        record("calendar.create", "PASS", f"id={event_id}")
    except Exception as e:
        record("calendar.create", "FAIL" if is_param_error(e) else "ERR",
               f"{type(e).__name__}: {str(e)[:120]}")

    if event_id:
        try:
            await fn(moodle_delete_calendar_event)(
                course_id=COURSE, event_id=event_id, repeat=False, ctx=ctx
            )
            record("calendar.delete", "PASS", f"deleted id={event_id}")
        except Exception as e:
            record("calendar.delete", "FAIL" if is_param_error(e) else "ERR",
                   f"{type(e).__name__}: {str(e)[:120]}")

    # ---- 3. ENROL shape-probe: enrol the current user (already enrolled ->
    #         idempotent no-op) to confirm the nested enrolments[] encoding.
    try:
        await fn(moodle_enrol_users)(
            course_id=COURSE, user_ids=[my_uid], role_id=5, ctx=ctx
        )
        record("enrol.users", "PASS", "nested enrolments[] accepted (idempotent)")
    except Exception as e:
        status = "FAIL" if is_param_error(e) else "PASS-SHAPE"
        record("enrol.users", status, f"{type(e).__name__}: {str(e)[:120]}")

    await client.close()
    return summarize()


def summarize():
    print("\n==== SUMMARY ====")
    bad = [r for r in results if r[1] == "FAIL"]
    for name, status, detail in results:
        print(f"  {status:10} {name}  {detail}")
    print(f"\nparam-encoding FAILURES: {len(bad)}")
    print("RESULT:", "GREEN (no param-encoding errors)" if not bad else "RED")
    return len(bad)


asyncio.run(main())
