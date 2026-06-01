"""
Course management tools - READ and WRITE operations for courses and categories.
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..core.exceptions import MoodleNotFoundError
from ..utils.error_handling import (
    handle_moodle_errors,
    require_global_write_permission,
    require_write_permission,
)
from ..utils.api_helpers import get_moodle_client, get_resolver
from ..models.courses import Course, CourseCategory, CourseSection


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to course tools.
# --------------------------------------------------------------------------- #
@dataclass
class CourseSummary:
    id: int
    fullname: str | None = None
    shortname: str | None = None
    categoryid: int | None = None
    categoryname: str | None = None
    startdate: int | None = None
    enddate: int | None = None
    visible: bool | None = None
    summary: str | None = None
    format: str | None = None


@dataclass
class CourseList:
    courses: list[CourseSummary] = field(default_factory=list)
    count: int = 0


@dataclass
class CourseSearchResult:
    courses: list[CourseSummary] = field(default_factory=list)
    total: int = 0
    showing: int = 0


@dataclass
class CourseDetails:
    id: int
    fullname: str | None = None
    shortname: str | None = None
    categoryid: int | None = None
    categoryname: str | None = None
    startdate: int | None = None
    enddate: int | None = None
    visible: bool | None = None
    summary: str | None = None
    format: str | None = None
    numsections: int | None = None
    showgrades: bool | None = None
    groupmode: int | None = None


@dataclass
class ModuleInfo:
    id: int
    name: str | None = None
    modname: str | None = None
    url: str | None = None
    visible: int | None = None
    uservisible: bool | None = None


@dataclass
class SectionInfo:
    id: int
    name: str | None = None
    section: int = 0
    summary: str | None = None
    visible: int | None = None
    modules: list[ModuleInfo] = field(default_factory=list)


@dataclass
class CourseContents:
    course_id: int
    sections: list[SectionInfo] = field(default_factory=list)
    count: int = 0


@dataclass
class EnrolledUser:
    id: int
    fullname: str | None = None
    email: str | None = None
    roles: list[str] = field(default_factory=list)


@dataclass
class EnrolledUsers:
    course_id: int
    users: list[EnrolledUser] = field(default_factory=list)
    total: int = 0
    showing: int = 0
    offset: int = 0


@dataclass
class CategoryInfo:
    id: int
    name: str | None = None
    parent: int | None = None
    description: str | None = None
    coursecount: int | None = None
    depth: int | None = None


@dataclass
class CategoryList:
    categories: list[CategoryInfo] = field(default_factory=list)
    count: int = 0


@dataclass
class CourseCreated:
    course_id: int | None = None
    fullname: str | None = None
    shortname: str | None = None
    category_id: int | None = None
    visible: bool | None = None


@dataclass
class CourseUpdated:
    course_id: int
    updated: bool = True


@dataclass
class CourseDeleted:
    course_id: int
    deleted: bool = True
    warning: str = "Course has been permanently deleted"


@dataclass
class CourseDuplicated:
    source_course_id: int
    new_course_id: int | None = None
    fullname: str | None = None
    shortname: str | None = None


@dataclass
class CourseImported:
    source_course_id: int
    dest_course_id: int
    imported: bool = True


@dataclass
class CategoryCreated:
    category_id: int | None = None
    name: str | None = None
    parent_id: int | None = None
    visible: bool | None = None


@dataclass
class CategoryDeleted:
    category_id: int
    deleted: bool = True
    recursive: bool = False
    warning: str = "Category has been permanently deleted"


def _course_summary(course: Course) -> CourseSummary:
    """Build a CourseSummary from a parsed Course model."""
    return CourseSummary(
        id=course.id,
        fullname=course.fullname,
        shortname=course.shortname,
        categoryid=course.categoryid,
        categoryname=course.categoryname,
        startdate=course.startdate,
        enddate=course.enddate,
        visible=course.visible,
        summary=course.summary,
        format=course.format,
    )


# ============================================================================
# READ OPERATIONS
# ============================================================================

@mcp.tool(
    name="moodle_list_user_courses",
    description=(
        "List the courses a user is enrolled in. Accepts a numeric user id, a "
        "username, or an email (omit for the current user). Optional: "
        "include_hidden (default False); recent=True to instead return only the "
        "user's recently-accessed courses, most-recent first, capped by limit. "
        "Example: user='jdoe', or recent=True, limit=5. Returns course ids "
        "needed for other course tools."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_list_user_courses(
    user: Annotated[
        int | str | None,
        Field(description="User id, username, or email; omit for current user"),
    ] = None,
    include_hidden: Annotated[
        bool, Field(description="Include hidden courses")
    ] = False,
    recent: Annotated[
        bool,
        Field(description="Return only recently-accessed courses, most-recent first"),
    ] = False,
    limit: Annotated[
        int, Field(description="Max results when recent=True", ge=1, le=50)
    ] = 10,
    ctx: Context = None,
) -> CourseList:
    """List a user's enrolled courses, or (recent=True) their recently-accessed
    courses sorted by most recent."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    uid = await resolver.user_id(user)

    if recent:
        # core_course_get_recent_courses is sorted by last access; fall back to
        # the enrolment list (capped) if the token's service lacks it.
        try:
            recent_data = await moodle.call(
                "core_course_get_recent_courses", {"userid": uid, "limit": limit}
            )
            courses = [Course(**c) for c in (recent_data or [])]
        except Exception:
            courses_data = await moodle.call(
                "core_enrol_get_users_courses", {"userid": uid}
            )
            courses = [Course(**c) for c in (courses_data or [])[:limit]]
        summaries = [_course_summary(c) for c in courses]
        return CourseList(courses=summaries, count=len(summaries))

    courses_data = await moodle.call(
        "core_enrol_get_users_courses", {"userid": uid}
    )

    courses = [Course(**course) for course in (courses_data or [])]
    if not include_hidden:
        courses = [c for c in courses if c.visible]

    summaries = [_course_summary(c) for c in courses]
    return CourseList(courses=summaries, count=len(summaries))


@mcp.tool(
    name="moodle_get_course_details",
    description=(
        "Get detailed course information including name, description, dates, "
        "format, and settings. Accepts a numeric course id, shortname, or "
        "idnumber. Example: course=2292 or course='CS101'."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_details(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    ctx: Context = None,
) -> CourseDetails:
    """Get a course's details by ID."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    courses_data = await moodle.call(
        "core_course_get_courses", {"options": {"ids": [cid]}}
    )
    if not courses_data:
        raise MoodleNotFoundError(f"Course {cid} not found.")

    c = Course(**courses_data[0])
    return CourseDetails(
        id=c.id,
        fullname=c.fullname,
        shortname=c.shortname,
        categoryid=c.categoryid,
        categoryname=c.categoryname,
        startdate=c.startdate,
        enddate=c.enddate,
        visible=c.visible,
        summary=c.summary,
        format=c.format,
        numsections=c.numsections,
        showgrades=c.showgrades,
        groupmode=c.groupmode,
    )


@mcp.tool(
    name="moodle_search_courses",
    description=(
        "Search for courses by name or description. Provide at least 1 "
        "character. Optional: limit (1-100, default 20). "
        "Example: search_query='Python'. Returns course ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_search_courses(
    search_query: Annotated[
        str, Field(description="Search term for course name/description", min_length=1)
    ],
    limit: Annotated[
        int, Field(description="Maximum results", ge=1, le=100)
    ] = 20,
    ctx: Context = None,
) -> CourseSearchResult:
    """Search courses by name or description."""
    moodle = get_moodle_client(ctx)

    search_data = await moodle.call(
        "core_course_search_courses",
        {"criterianame": "search", "criteriavalue": search_query},
    )

    courses_data = (search_data or {}).get("courses", [])
    total = (search_data or {}).get("total", len(courses_data))

    courses = [Course(**course) for course in courses_data[:limit]]
    summaries = [_course_summary(c) for c in courses]
    return CourseSearchResult(
        courses=summaries, total=total, showing=len(summaries)
    )


@mcp.tool(
    name="moodle_get_course_contents",
    description=(
        "Get full course content structure including sections, modules, "
        "activities, and resources. Accepts a numeric course id, shortname, "
        "or idnumber. Example: course=2292 or course='CS101'."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_contents(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    ctx: Context = None,
) -> CourseContents:
    """Get a course's section/module content structure."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    contents_data = await moodle.call(
        "core_course_get_contents", {"courseid": cid}
    )
    if not contents_data:
        raise MoodleNotFoundError(f"No content found for course {cid}.")

    sections: list[SectionInfo] = []
    for raw_section in contents_data:
        s = CourseSection(**raw_section)
        sections.append(
            SectionInfo(
                id=s.id,
                name=s.name,
                section=s.section,
                summary=s.summary,
                visible=s.visible,
                modules=[
                    ModuleInfo(
                        id=m.id,
                        name=m.name,
                        modname=m.modname,
                        url=m.url,
                        visible=m.visible,
                        uservisible=m.uservisible,
                    )
                    for m in s.modules
                ],
            )
        )

    return CourseContents(course_id=cid, sections=sections, count=len(sections))


@mcp.tool(
    name="moodle_get_enrolled_users",
    description=(
        "Get list of all users enrolled in a course. Accepts a numeric course "
        "id, shortname, or idnumber. Optional: limit (1-100, default 20), "
        "offset (default 0). Example: course=2292. Returns user ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_enrolled_users(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    limit: Annotated[
        int, Field(description="Maximum results", ge=1, le=100)
    ] = 20,
    offset: Annotated[
        int, Field(description="Offset for pagination", ge=0)
    ] = 0,
    ctx: Context = None,
) -> EnrolledUsers:
    """List users enrolled in a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    users_data = await moodle.call(
        "core_enrol_get_enrolled_users", {"courseid": cid}
    )
    users_data = users_data or []

    total = len(users_data)
    page = users_data[offset:offset + limit]

    users = [
        EnrolledUser(
            id=u.get("id", 0),
            fullname=u.get("fullname"),
            email=u.get("email"),
            roles=[r.get("shortname", "") for r in (u.get("roles", []) or [])],
        )
        for u in page
    ]

    return EnrolledUsers(
        course_id=cid,
        users=users,
        total=total,
        showing=len(users),
        offset=offset,
    )


@mcp.tool(
    name="moodle_get_course_categories",
    description=(
        "Get all course categories from the Moodle site. No parameters. "
        "Useful for browsing course organization and discovering category ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_course_categories(ctx: Context = None) -> CategoryList:
    """List course categories on the site."""
    moodle = get_moodle_client(ctx)

    categories_data = await moodle.call("core_course_get_categories")
    if not categories_data:
        return CategoryList(categories=[], count=0)

    categories = [CourseCategory(**cat) for cat in categories_data]
    infos = [
        CategoryInfo(
            id=c.id,
            name=c.name,
            parent=c.parent,
            description=c.description,
            coursecount=c.coursecount,
            depth=c.depth,
        )
        for c in categories
    ]
    return CategoryList(categories=infos, count=len(infos))


@mcp.tool(
    name="moodle_create_course",
    description=(
        "Create a new course (requires admin permissions). REQUIRED: fullname, "
        "shortname, category_id. Optional: summary, course_format, visible. "
        "ADMIN ONLY. Returns the new course id."
    ),
    tags={"write", "course"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_global_write_permission
async def moodle_create_course(
    fullname: Annotated[
        str, Field(description="Full name of the course", min_length=1)
    ],
    shortname: Annotated[
        str, Field(description="Short name/code for the course", min_length=1)
    ],
    category_id: Annotated[
        int, Field(description="Category ID where course will be created", gt=0)
    ],
    summary: Annotated[
        str | None, Field(description="Course summary/description")
    ] = None,
    course_format: Annotated[
        str, Field(description="Course format (topics, weeks, social)")
    ] = "topics",
    visible: Annotated[
        bool, Field(description="Whether course is visible to students")
    ] = True,
    ctx: Context = None,
) -> CourseCreated:
    """Create a new course (admin only)."""
    moodle = get_moodle_client(ctx)

    course: dict = {
        "fullname": fullname,
        "shortname": shortname,
        "categoryid": category_id,
        "format": course_format,
        "visible": visible,
    }
    if summary:
        course["summary"] = summary

    result = await moodle.call(
        "core_course_create_courses", {"courses": [course]}
    )
    if not result:
        raise MoodleNotFoundError(
            "Failed to create course - no result returned"
        )

    return CourseCreated(
        course_id=result[0].get("id"),
        fullname=fullname,
        shortname=shortname,
        category_id=category_id,
        visible=visible,
    )


@mcp.tool(
    name="moodle_update_course",
    description=(
        "Update an existing course (requires admin/teacher permissions). "
        "REQUIRED: course_id. Optional: fullname, shortname, summary, visible. "
        "Can only update whitelisted courses in dev mode."
    ),
    tags={"write", "course"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_update_course(
    course_id: Annotated[
        int, Field(description="Course ID to update", gt=0)
    ],
    fullname: Annotated[
        str | None, Field(description="New full name")
    ] = None,
    shortname: Annotated[
        str | None, Field(description="New short name")
    ] = None,
    summary: Annotated[
        str | None, Field(description="New summary/description")
    ] = None,
    visible: Annotated[
        bool | None, Field(description="New visibility status")
    ] = None,
    ctx: Context = None,
) -> CourseUpdated:
    """Update an existing course's properties (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    course: dict = {"id": course_id}
    if fullname is not None:
        course["fullname"] = fullname
    if shortname is not None:
        course["shortname"] = shortname
    if summary is not None:
        course["summary"] = summary
    if visible is not None:
        course["visible"] = visible

    if len(course) == 1:
        raise ValueError(
            "No updates specified. Please provide at least one field to update."
        )

    await moodle.call("core_course_update_courses", {"courses": [course]})
    return CourseUpdated(course_id=course_id, updated=True)


@mcp.tool(
    name="moodle_delete_course",
    description=(
        "Delete a course permanently (requires admin permissions). REQUIRED: "
        "course_id. DESTRUCTIVE OPERATION - Cannot be undone! ADMIN ONLY. "
        "Only works on whitelisted courses in dev mode."
    ),
    tags={"write", "course", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_delete_course(
    course_id: Annotated[
        int, Field(description="Course ID to delete (must be whitelisted!)", gt=0)
    ],
    ctx: Context = None,
) -> CourseDeleted:
    """Permanently delete a course (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)
    await moodle.call("core_course_delete_courses", {"courseids": [course_id]})
    return CourseDeleted(course_id=course_id, deleted=True)


@mcp.tool(
    name="moodle_duplicate_course",
    description=(
        "Duplicate an existing course (requires admin/teacher permissions). "
        "REQUIRED: course_id, fullname, shortname, category_id. Optional: "
        "visible. Source course must be whitelisted in dev mode."
    ),
    tags={"write", "course"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_duplicate_course(
    course_id: Annotated[
        int,
        Field(description="Source course ID to duplicate (must be whitelisted!)", gt=0),
    ],
    fullname: Annotated[
        str, Field(description="Full name for new course", min_length=1)
    ],
    shortname: Annotated[
        str, Field(description="Short name for new course", min_length=1)
    ],
    category_id: Annotated[
        int, Field(description="Category ID for new course", gt=0)
    ],
    visible: Annotated[
        bool, Field(description="Whether new course is visible")
    ] = True,
    ctx: Context = None,
) -> CourseDuplicated:
    """Duplicate a course with its activities and settings (whitelisted source only)."""
    moodle = get_moodle_client(ctx)

    result = await moodle.call(
        "core_course_duplicate_course",
        {
            "courseid": course_id,
            "fullname": fullname,
            "shortname": shortname,
            "categoryid": category_id,
            "visible": visible,
        },
    )

    return CourseDuplicated(
        source_course_id=course_id,
        new_course_id=result.get("id") if result else None,
        fullname=fullname,
        shortname=shortname,
    )


@mcp.tool(
    name="moodle_import_course_content",
    description=(
        "Import content from one course to another (requires admin/teacher "
        "permissions). REQUIRED: source_course_id, dest_course_id. Both courses "
        "must be whitelisted in dev mode."
    ),
    tags={"write", "course"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('source_course_id')
@require_write_permission('dest_course_id')
async def moodle_import_course_content(
    source_course_id: Annotated[
        int,
        Field(description="Source course ID to import from (must be whitelisted!)", gt=0),
    ],
    dest_course_id: Annotated[
        int,
        Field(description="Destination course ID to import to (must be whitelisted!)", gt=0),
    ],
    ctx: Context = None,
) -> CourseImported:
    """Import activities/content from one course into another (both whitelisted)."""
    moodle = get_moodle_client(ctx)

    await moodle.call(
        "core_course_import_course",
        {
            "importfrom": source_course_id,
            "importto": dest_course_id,
            "deletecontent": 0,  # Don't delete existing content
        },
    )

    return CourseImported(
        source_course_id=source_course_id,
        dest_course_id=dest_course_id,
        imported=True,
    )


@mcp.tool(
    name="moodle_create_course_category",
    description=(
        "Create a new course category (requires admin permissions). REQUIRED: "
        "name. Optional: parent_id, description, visible. ADMIN ONLY. Returns "
        "the new category id."
    ),
    tags={"write", "course"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_global_write_permission
async def moodle_create_course_category(
    name: Annotated[
        str, Field(description="Category name", min_length=1)
    ],
    parent_id: Annotated[
        int, Field(description="Parent category ID (0 for top level)", ge=0)
    ] = 0,
    description: Annotated[
        str | None, Field(description="Category description")
    ] = None,
    visible: Annotated[
        bool, Field(description="Whether category is visible")
    ] = True,
    ctx: Context = None,
) -> CategoryCreated:
    """Create a new course category (admin only)."""
    moodle = get_moodle_client(ctx)

    category: dict = {
        "name": name,
        "parent": parent_id,
        "visible": visible,
    }
    if description:
        category["description"] = description

    result = await moodle.call(
        "core_course_create_categories", {"categories": [category]}
    )
    if not result:
        raise MoodleNotFoundError(
            "Failed to create category - no result returned"
        )

    return CategoryCreated(
        category_id=result[0].get("id"),
        name=name,
        parent_id=parent_id,
        visible=visible,
    )


@mcp.tool(
    name="moodle_delete_course_category",
    description=(
        "Delete a course category permanently (requires admin permissions). "
        "REQUIRED: category_id. Optional: recursive (default False). "
        "DESTRUCTIVE OPERATION - Cannot be undone! ADMIN ONLY. If "
        "recursive=True, deletes all courses in category!"
    ),
    tags={"write", "course", "destructive"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_global_write_permission
async def moodle_delete_course_category(
    category_id: Annotated[
        int, Field(description="Category ID to delete", gt=0)
    ],
    recursive: Annotated[
        bool,
        Field(description="Also delete all courses in category (DANGEROUS!)"),
    ] = False,
    confirm: Annotated[
        bool,
        Field(
            description=(
                "Must be set to True to allow recursive deletion. Ignored when "
                "recursive=False. Guards against accidentally cascade-deleting "
                "every course in the category."
            )
        ),
    ] = False,
    ctx: Context = None,
) -> CategoryDeleted:
    """Permanently delete a course category (admin only)."""
    if recursive and not confirm:
        raise ValueError(
            "Recursive category deletion cascade-deletes EVERY course in the "
            "category and cannot be undone. Re-call with confirm=True to proceed."
        )

    moodle = get_moodle_client(ctx)

    await moodle.call(
        "core_course_delete_categories",
        {"categories": [{"id": category_id, "recursive": recursive}]},
    )

    warning = "Category has been permanently deleted" + (
        " along with all its courses" if recursive else ""
    )
    return CategoryDeleted(
        category_id=category_id,
        deleted=True,
        recursive=recursive,
        warning=warning,
    )
