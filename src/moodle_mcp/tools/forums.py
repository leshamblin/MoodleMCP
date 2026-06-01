"""
Forum discussion tools - READ and WRITE operations.
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client, get_resolver


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to forum tools.
# --------------------------------------------------------------------------- #
@dataclass
class ForumDiscussion:
    id: int
    name: str | None = None
    subject: str | None = None
    forum_name: str | None = None
    course_name: str | None = None
    user_fullname: str | None = None
    created: int | None = None
    modified: int | None = None
    num_replies: int | None = None


@dataclass
class ForumDiscussionList:
    course_id: int
    discussions: list[ForumDiscussion] = field(default_factory=list)
    count: int = 0


@dataclass
class ForumSearchResult:
    search_query: str
    discussions: list[ForumDiscussion] = field(default_factory=list)
    count: int = 0


@dataclass
class ForumPost:
    id: int
    subject: str | None = None
    message: str | None = None
    author_fullname: str | None = None
    created: int | None = None
    parent_id: int | None = None


@dataclass
class DiscussionPosts:
    discussion_id: int
    posts: list[ForumPost] = field(default_factory=list)
    count: int = 0


@dataclass
class CreatedDiscussion:
    discussion_id: int
    forum_id: int
    course_id: int
    subject: str
    pinned: bool


@dataclass
class CreatedPost:
    new_post_id: int
    replied_to_post_id: int
    course_id: int
    subject: str


def _discussion(data: dict) -> ForumDiscussion:
    """Build a ForumDiscussion from a raw Moodle discussion dict."""
    return ForumDiscussion(
        id=data.get("discussion", data.get("id", 0)),
        name=data.get("name"),
        subject=data.get("subject"),
        forum_name=data.get("forumname"),
        course_name=data.get("coursename"),
        user_fullname=data.get("userfullname"),
        created=data.get("created"),
        modified=data.get("modified") or data.get("timemodified"),
        num_replies=data.get("numreplies"),
    )


@mcp.tool(
    name="moodle_get_forum_discussions",
    description=(
        "Get forum discussions in a course. Accepts a numeric course id, "
        "shortname, or idnumber. Optional: limit (1-100, default=20). "
        "Example: course=2292. Returns discussion ids."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_forum_discussions(
    course: Annotated[
        int | str, Field(description="Course id, shortname, or idnumber")
    ],
    limit: Annotated[
        int, Field(description="Maximum discussions to return", ge=1, le=100)
    ] = 20,
    ctx: Context = None,
) -> ForumDiscussionList:
    """List discussions across all forums in a course."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)
    cid = await resolver.course_id(course)

    forums_data = await moodle.call(
        "mod_forum_get_forums_by_courses", {"courseids": [cid]}
    )
    forums = forums_data if isinstance(forums_data, list) else []

    all_discussions: list[ForumDiscussion] = []
    for forum in forums[:5]:  # limit forums to avoid too many requests
        try:
            discussions_data = await moodle.call(
                "mod_forum_get_forum_discussions",
                {"forumid": forum["id"], "perpage": limit},
            )
        except Exception:
            continue
        for disc in discussions_data.get("discussions", []):
            disc["forumname"] = forum.get("name", "Unknown Forum")
            all_discussions.append(_discussion(disc))

    all_discussions = all_discussions[:limit]
    return ForumDiscussionList(
        course_id=cid, discussions=all_discussions, count=len(all_discussions)
    )


@mcp.tool(
    name="moodle_get_discussion_posts",
    description=(
        "Get all posts from a forum discussion. REQUIRED: discussion_id "
        "(integer). Example: discussion_id=789. Use "
        "moodle_get_forum_discussions to get discussion_id."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_discussion_posts(
    discussion_id: Annotated[int, Field(description="Discussion ID", gt=0)],
    ctx: Context = None,
) -> DiscussionPosts:
    """Get all posts in a forum discussion."""
    moodle = get_moodle_client(ctx)

    posts_data = await moodle.call(
        "mod_forum_get_discussion_posts", {"discussionid": discussion_id}
    )

    posts = [
        ForumPost(
            id=p.get("id", 0),
            subject=p.get("subject"),
            message=p.get("message"),
            author_fullname=(p.get("author") or {}).get("fullname"),
            created=p.get("timecreated"),
            parent_id=p.get("parentid"),
        )
        for p in (posts_data or {}).get("posts", [])
    ]
    return DiscussionPosts(
        discussion_id=discussion_id, posts=posts, count=len(posts)
    )


@mcp.tool(
    name="moodle_search_forums",
    description=(
        "Search forum posts and discussions. REQUIRED: search_query (string, "
        "min 2 chars). Optional: course (id, shortname, or idnumber) to limit "
        "search, limit (1-100, default=20). "
        "Example: search_query='homework', course=2292."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_search_forums(
    search_query: Annotated[
        str, Field(description="Search term", min_length=2)
    ],
    course: Annotated[
        int | str | None,
        Field(description="Optional course id, shortname, or idnumber to limit search"),
    ] = None,
    limit: Annotated[
        int, Field(description="Maximum results", ge=1, le=100)
    ] = 20,
    ctx: Context = None,
) -> ForumSearchResult:
    """Search forum discussions by keyword across the user's courses."""
    moodle = get_moodle_client(ctx)
    resolver = get_resolver(ctx)

    site_info = await moodle.get_site_info()
    user_id = site_info["userid"]

    courses_data = await moodle.call(
        "core_enrol_get_users_courses", {"userid": user_id}
    )

    if course is not None:
        cid = await resolver.course_id(course)
        courses_data = [c for c in courses_data if c["id"] == cid]

    needle = search_query.lower()
    matches: list[ForumDiscussion] = []
    for crs in courses_data[:10]:  # limit courses to avoid too many requests
        try:
            forums_data = await moodle.call(
                "mod_forum_get_forums_by_courses", {"courseids": [crs["id"]]}
            )
        except Exception:
            continue
        forums = forums_data if isinstance(forums_data, list) else []

        for forum in forums[:3]:  # limit forums per course
            try:
                discussions_data = await moodle.call(
                    "mod_forum_get_forum_discussions", {"forumid": forum["id"]}
                )
            except Exception:
                continue

            for disc in discussions_data.get("discussions", []):
                name = (disc.get("name") or "").lower()
                message = (disc.get("message") or "").lower()
                if needle in name or needle in message:
                    disc["coursename"] = crs.get("fullname")
                    disc["forumname"] = forum.get("name", "Unknown")
                    matches.append(_discussion(disc))
                    if len(matches) >= limit:
                        break
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break

    matches = matches[:limit]
    return ForumSearchResult(
        search_query=search_query, discussions=matches, count=len(matches)
    )


# ============================================================================
# WRITE OPERATIONS - Require write permission and course whitelist
# ============================================================================

@mcp.tool(
    name="moodle_create_forum_discussion",
    description=(
        "Create a new forum discussion/post. REQUIRED: course_id (integer), "
        "forum_id (forum INSTANCE id, integer), subject (string), message "
        "(string). Optional: pinned (boolean, default=False). WRITE OPERATION "
        "- only works on whitelisted courses (default: course 7299). "
        "Example: course_id=7299, forum_id=123, subject='New Topic', "
        "message='Discussion content'."
    ),
    tags={"write", "forum"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_create_forum_discussion(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    forum_id: Annotated[
        int,
        Field(description="Forum INSTANCE id where discussion will be created", gt=0),
    ],
    subject: Annotated[
        str, Field(description="Discussion subject/title", min_length=1, max_length=255)
    ],
    message: Annotated[
        str, Field(description="Discussion message content", min_length=1)
    ],
    pinned: Annotated[
        bool, Field(description="Pin the discussion to top")
    ] = False,
    ctx: Context = None,
) -> CreatedDiscussion:
    """Create a new discussion topic in a forum (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    # mod_forum_add_discussion renders the message as HTML by default and does
    # NOT accept a 'messageformat' parameter/option -- passing one is rejected
    # (errorinvalidparam). Verified live: an HTML body renders unescaped without
    # any format option. Only discussionsubscribe/discussionpinned/attachment
    # options are valid here. Do not add messageformat.
    result = await moodle.call(
        "mod_forum_add_discussion",
        {
            "forumid": forum_id,
            "subject": subject,
            "message": message,
            "options": [{"name": "discussionpinned", "value": pinned}],
        },
    )

    return CreatedDiscussion(
        discussion_id=(result or {}).get("discussionid", 0),
        forum_id=forum_id,
        course_id=course_id,
        subject=subject,
        pinned=pinned,
    )


@mcp.tool(
    name="moodle_add_forum_post",
    description=(
        "Reply to an existing forum discussion post. REQUIRED: course_id "
        "(integer), post_id (integer), subject (string), message (string). "
        "WRITE OPERATION - only works on whitelisted courses (default: course "
        "7299). Example: course_id=7299, post_id=456, subject='Re: Topic', "
        "message='Reply content'. Use moodle_get_discussion_posts to get "
        "post_id."
    ),
    tags={"write", "forum"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_add_forum_post(
    course_id: Annotated[
        int, Field(description="Course ID (must be whitelisted)", gt=0)
    ],
    post_id: Annotated[int, Field(description="Post ID to reply to", gt=0)],
    subject: Annotated[
        str, Field(description="Reply subject/title", min_length=1, max_length=255)
    ],
    message: Annotated[
        str, Field(description="Reply message content", min_length=1)
    ],
    ctx: Context = None,
) -> CreatedPost:
    """Reply to an existing forum discussion post (whitelisted courses only)."""
    moodle = get_moodle_client(ctx)

    result = await moodle.call(
        "mod_forum_add_discussion_post",
        {
            "postid": post_id,
            "subject": subject,
            "message": message,
            "options": [{"name": "messageformat", "value": 1}],  # HTML format
        },
    )

    return CreatedPost(
        new_post_id=(result or {}).get("postid", 0),
        replied_to_post_id=post_id,
        course_id=course_id,
        subject=subject,
    )
