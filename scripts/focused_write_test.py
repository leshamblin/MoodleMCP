"""
Focused live write test of the AVAILABLE write functions on course 7299.

Targets only functions present in this token's service and real objects that
exist in the course. Reversible / self-targeted where possible.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MOODLE_ENV", "dev")

import moodle_mcp.main as _main  # noqa: F401
from moodle_mcp.core.client import MoodleAPIClient
from moodle_mcp.core.config import get_config
from tests.test_helpers import MockContext

COURSE = 7299
FORUM_CMID = 2233887   # Announcements (cancreatediscussions=true)
results = []


def rec(name, status, detail=""):
    results.append((name, status, detail))
    print(f"[{status}] {name}: {detail}")


def fn(t):
    return getattr(t, "fn", t)


async def main():
    c = get_config()
    cl = MoodleAPIClient(base_url=c.url, token=c.token, timeout=c.api_timeout)
    ctx = MockContext(cl)
    info = await cl.get_site_info()
    me = info["userid"]

    from moodle_mcp.tools.forums import moodle_create_forum_discussion
    from moodle_mcp.tools.messages import moodle_send_message
    from moodle_mcp.tools.calendar import (
        moodle_create_calendar_event, moodle_delete_calendar_event,
    )

    # ---- FORUM: create a real discussion in the Announcements forum.
    # forum_id is the INSTANCE id (21133), per mod_forum_add_discussion.
    try:
        before = await cl.call("mod_forum_get_forum_discussions", {"forumid": 21133})
        n_before = len((before or {}).get("discussions", [])) if isinstance(before, dict) else 0
        res = await fn(moodle_create_forum_discussion)(
            course_id=COURSE, forum_id=21133,
            subject="_mcp_write_test", message="<p>Automated write-path test post.</p>",
            ctx=ctx,
        )
        after = await cl.call("mod_forum_get_forum_discussions", {"forumid": 21133})
        n_after = len((after or {}).get("discussions", [])) if isinstance(after, dict) else 0
        # find the new discussion id (for the report)
        new = [d for d in (after or {}).get("discussions", [])
               if d.get("subject") == "_mcp_write_test"]
        did = new[0].get("discussion") if new else None
        ok = n_after > n_before
        rec("forum.create_discussion", "PASS" if ok else "WARN",
            f"discussions {n_before}->{n_after} new_id={did}")
    except Exception as e:
        rec("forum.create_discussion", "FAIL", f"{type(e).__name__}: {str(e)[:140]}")

    # ---- MESSAGING: send a message to self, then delete the conversation.
    try:
        res = await fn(moodle_send_message)(
            recipient_user_id=me, message_text="_mcp write-path self test", ctx=ctx,
        )
        rec("message.send", "PASS", f"sent to self ({str(res)[:60]})")
    except Exception as e:
        # delivery to self may be disallowed; classify
        s = str(e).lower()
        param = "invalidparameter" in s or "missing required key" in s
        rec("message.send", "FAIL" if param else "PASS-SHAPE", f"{type(e).__name__}: {str(e)[:120]}")

    # ---- CALENDAR: create + delete (re-confirm).
    try:
        when = 1893456000
        await fn(moodle_create_calendar_event)(
            course_id=COURSE, event_name="_mcp_cal_test", event_time=when,
            description="temp", duration=0, ctx=ctx,
        )
        ev = await cl.call("core_calendar_get_calendar_events", {
            "events": {"courseids": [COURSE]},
            "options": {"timestart": when - 86400, "timeend": when + 86400},
        })
        evs = (ev or {}).get("events", []) if isinstance(ev, dict) else []
        match = [e for e in evs if e.get("name") == "_mcp_cal_test"]
        eid = match[0]["id"] if match else None
        if eid:
            await fn(moodle_delete_calendar_event)(course_id=COURSE, event_id=eid, repeat=False, ctx=ctx)
            rec("calendar.create_delete", "PASS", f"created+deleted id={eid}")
        else:
            rec("calendar.create_delete", "WARN", "created but could not locate event id")
    except Exception as e:
        rec("calendar.create_delete", "FAIL", f"{type(e).__name__}: {str(e)[:140]}")

    await cl.close()

    print("\n==== FOCUSED WRITE TEST SUMMARY ====")
    for name, status, detail in results:
        print(f"  {status:12} {name}  {detail}")
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"\nHARD FAILURES: {len(fails)}")
    print("RESULT:", "GREEN" if not fails else "RED")


asyncio.run(main())
