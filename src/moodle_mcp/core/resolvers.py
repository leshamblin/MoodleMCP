"""
Identifier resolution: map human-friendly references to internal Moodle IDs.

Agents shouldn't have to chain ``search_users`` -> id -> ``get_grades``. The
resolver lets a tool accept either a numeric id or a human-friendly string
(email/username, course shortname/idnumber, activity name) and turns it into
the internal id the Moodle function needs.

Resolution is memoized per resolver instance. A resolver is created once per
tool call (see ``utils.api_helpers.get_resolver``) so repeated lookups within
one call are cheap, while staleness across calls is avoided.

ID semantics (important): Moodle activity functions disagree about which id
they want. ``ActivityIds`` carries both:
  - ``cmid``     -> course module id   (e.g. core_grades_update_grades.activityid)
  - ``instance`` -> activity instance  (e.g. mod_assign_*, mod_quiz_*,
                                         mod_forum_add_discussion.forumid)
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from .exceptions import AmbiguousIdentifierError, IdentifierNotFoundError

if TYPE_CHECKING:
    from .client import MoodleAPIClient

# A reference may be an int id or a human-friendly string.
UserRef = Union[int, str]      # id | username | email
CourseRef = Union[int, str]    # id | shortname | idnumber
ActivityRef = Union[int, str]  # cmid | activity name within a course


@dataclass(frozen=True)
class ActivityIds:
    """Both ids for a course activity, plus its type and name."""
    cmid: int
    instance: int
    modname: str
    name: str


class MoodleResolver:
    """Resolve human-friendly references to internal Moodle ids (memoized)."""

    def __init__(self, client: "MoodleAPIClient"):
        self.client = client
        self._user_cache: dict[str, int] = {}
        self._course_cache: dict[str, int] = {}
        self._contents_cache: dict[int, list] = {}
        self._current_user_id: int | None = None

    # ------------------------------------------------------------------ users
    async def user_id(self, ref: UserRef | None) -> int:
        """
        Resolve a user reference to a numeric user id.

        - ``None`` -> the current (token) user
        - ``int``  -> returned unchanged
        - ``str``  -> looked up by email (if it contains '@') else username,
          falling back to email.
        """
        if ref is None:
            if self._current_user_id is None:
                info = await self.client.get_site_info()
                self._current_user_id = info["userid"]
            return self._current_user_id
        if isinstance(ref, int):
            return ref

        key = ref.strip()
        if key in self._user_cache:
            return self._user_cache[key]

        if "@" in key:
            uid = await self._lookup_user_field("email", key)
        else:
            uid = await self._lookup_user_field("username", key, required=False)
            if uid is None:
                uid = await self._lookup_user_field("email", key)

        self._user_cache[key] = uid
        return uid

    async def _lookup_user_field(
        self, field: str, value: str, required: bool = True
    ) -> int | None:
        data = await self.client.call(
            "core_user_get_users_by_field", {"field": field, "values": [value]}
        )
        users = data or []
        if not users:
            if required:
                raise IdentifierNotFoundError(
                    f"No user found with {field}={value!r}"
                )
            return None
        if len(users) > 1:
            raise AmbiguousIdentifierError(
                f"{len(users)} users match {field}={value!r}: "
                + ", ".join(f"{u.get('fullname')} (id {u.get('id')})" for u in users)
            )
        return users[0]["id"]

    # ---------------------------------------------------------------- courses
    async def course_id(self, ref: CourseRef) -> int:
        """
        Resolve a course reference to a numeric course id.

        - ``int`` -> returned unchanged
        - ``str`` -> looked up by shortname, falling back to idnumber.
        """
        if isinstance(ref, int):
            return ref

        key = ref.strip()
        if key in self._course_cache:
            return self._course_cache[key]

        cid = await self._lookup_course_field("shortname", key, required=False)
        if cid is None:
            cid = await self._lookup_course_field("idnumber", key)

        self._course_cache[key] = cid
        return cid

    async def _lookup_course_field(
        self, field: str, value: str, required: bool = True
    ) -> int | None:
        data = await self.client.call(
            "core_course_get_courses_by_field", {"field": field, "value": value}
        )
        courses = (data or {}).get("courses", []) if isinstance(data, dict) else []
        if not courses:
            if required:
                raise IdentifierNotFoundError(
                    f"No course found with {field}={value!r}"
                )
            return None
        if len(courses) > 1:
            raise AmbiguousIdentifierError(
                f"{len(courses)} courses match {field}={value!r}: "
                + ", ".join(
                    f"{c.get('shortname')} (id {c.get('id')})" for c in courses
                )
            )
        return courses[0]["id"]

    # ------------------------------------------------------------- activities
    async def activity(
        self,
        course: CourseRef,
        ref: ActivityRef,
        modname: str | None = None,
    ) -> ActivityIds:
        """
        Resolve an activity reference within a course to its ids.

        - ``int`` ref -> matched against module cmid
        - ``str`` ref -> matched (case-insensitive) against module name,
          optionally filtered by ``modname`` (e.g. 'assign', 'quiz', 'forum').

        Returns an :class:`ActivityIds` with both cmid and instance.
        """
        cid = await self.course_id(course)
        modules = await self._course_modules(cid)

        if modname:
            modules = [m for m in modules if m.get("modname") == modname]

        if isinstance(ref, int):
            matches = [m for m in modules if m.get("id") == ref]
        else:
            target = ref.strip().casefold()
            matches = [m for m in modules if (m.get("name") or "").casefold() == target]

        if not matches:
            raise IdentifierNotFoundError(
                f"No activity matching {ref!r} in course {cid}"
                + (f" (modname={modname})" if modname else "")
            )
        if len(matches) > 1:
            raise AmbiguousIdentifierError(
                f"{len(matches)} activities match {ref!r} in course {cid}: "
                + ", ".join(
                    f"{m.get('name')} ({m.get('modname')} cmid {m.get('id')})"
                    for m in matches
                )
                + ". Pass modname to disambiguate."
            )

        m = matches[0]
        return ActivityIds(
            cmid=m["id"],
            instance=m.get("instance", m["id"]),
            modname=m.get("modname", ""),
            name=m.get("name", ""),
        )

    async def _course_modules(self, course_id: int) -> list[dict]:
        """Flattened list of all modules in a course (cached per course)."""
        if course_id not in self._contents_cache:
            contents = await self.client.call(
                "core_course_get_contents", {"courseid": course_id}
            )
            modules: list[dict] = []
            for section in contents or []:
                modules.extend(section.get("modules", []) or [])
            self._contents_cache[course_id] = modules
        return self._contents_cache[course_id]
