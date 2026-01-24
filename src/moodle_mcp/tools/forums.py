"""
Forum discussion tools - READ and WRITE operations.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

@mcp.tool(
    name="moodle_get_forum_discussions",
    description="Get forum discussions in a course. REQUIRED: course_id (integer). Optional: limit (1-100, default=20). Example: course_id=2292. Returns discussion IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_forum_discussions(
    course_id: int = Field(description="Course ID", gt=0),
    limit: int = Field(default=20, description="Maximum discussions to return", ge=1, le=100),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of forum discussions in a course.

    Shows all forum discussions across all forums in a course.

    Args:
        course_id: Course ID
        limit: Maximum number of discussions
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of forum discussions

    Example use cases:
        - "What forum discussions are in course 42?"
        - "Show forum posts in course 15"
        - "List discussions for course 8"
    """
    moodle = get_moodle_client(ctx)

    # First get forums in course
    try:
        forums_data = await moodle._make_request(
            'mod_forum_get_forums_by_courses',
            {'courseids[0]': course_id}
        )

        forums = forums_data if isinstance(forums_data, list) else []

        if not forums:
            return f"No forums found in course {course_id}."

        # Get discussions from each forum
        all_discussions = []
        for forum in forums[:5]:  # Limit to first 5 forums to avoid too many requests
            try:
                discussions_data = await moodle._make_request(
                    'mod_forum_get_forum_discussions',
                    {
                        'forumid': forum['id'],
                        'perpage': limit
                    }
                )

                discussions = discussions_data.get('discussions', [])
                for disc in discussions:
                    disc['forumname'] = forum.get('name', 'Unknown Forum')
                    all_discussions.append(disc)
            except Exception:
                continue

        if not all_discussions:
            return f"No discussions found in forums for course {course_id}."

        # Limit total discussions
        all_discussions = all_discussions[:limit]

        return format_response(all_discussions, f"Forum Discussions (Course {course_id})", format)
    except Exception as e:
        return f"Unable to retrieve forum discussions for course {course_id}. Error: {str(e)}"

@mcp.tool(
    name="moodle_get_discussion_posts",
    description="Get all posts from a forum discussion. REQUIRED: discussion_id (integer). Example: discussion_id=789. Use moodle_get_forum_discussions to get discussion_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_discussion_posts(
    discussion_id: int = Field(description="Discussion ID", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get all posts from a specific forum discussion.

    Shows the discussion thread with all replies.

    Args:
        discussion_id: Discussion ID
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Posts in the discussion

    Example use cases:
        - "Show posts in discussion 123"
        - "Read discussion 45"
        - "Get forum thread 67"
    """
    moodle = get_moodle_client(ctx)

    try:
        posts_data = await moodle._make_request(
            'mod_forum_get_discussion_posts',
            {'discussionid': discussion_id}
        )

        posts = posts_data.get('posts', [])

        if not posts:
            return f"No posts found in discussion {discussion_id}."

        return format_response(posts, f"Discussion Posts (Discussion {discussion_id})", format)
    except Exception as e:
        return f"Unable to retrieve posts from discussion {discussion_id}. Error: {str(e)}"

@mcp.tool(
    name="moodle_search_forums",
    description="Search forum posts and discussions. REQUIRED: search_query (string, min 2 chars). Optional: course_id (integer) to limit search, limit (1-100, default=20). Example: search_query='homework', course_id=2292.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_search_forums(
    search_query: str = Field(description="Search term", min_length=2),
    course_id: int | None = Field(None, description="Optional course ID to limit search"),
    limit: int = Field(default=20, description="Maximum results", ge=1, le=100),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Search forum discussions and posts by keyword.

    Searches across forum discussions and posts for matching content.

    Args:
        search_query: Search term
        course_id: Optional course ID to limit search
        limit: Maximum number of results
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Matching forum discussions/posts

    Example use cases:
        - "Search forums for 'Python'"
        - "Find forum posts about 'homework'"
        - "Search course 42 forums for 'deadline'"
    """
    moodle = get_moodle_client(ctx)

    try:
        # Get user's courses
        site_info = await moodle.get_site_info()
        user_id = site_info['userid']

        courses_data = await moodle._make_request(
            'core_enrol_get_users_courses',
            {'userid': user_id}
        )

        # Filter to specific course if provided
        if course_id:
            courses_data = [c for c in courses_data if c['id'] == course_id]

        # Search through forums
        matching_discussions = []
        for course in courses_data[:10]:  # Limit to 10 courses to avoid too many requests
            try:
                forums_data = await moodle._make_request(
                    'mod_forum_get_forums_by_courses',
                    {'courseids[0]': course['id']}
                )

                forums = forums_data if isinstance(forums_data, list) else []

                for forum in forums[:3]:  # Limit forums per course
                    try:
                        discussions_data = await moodle._make_request(
                            'mod_forum_get_forum_discussions',
                            {'forumid': forum['id']}
                        )

                        discussions = discussions_data.get('discussions', [])

                        # Filter by search query
                        for disc in discussions:
                            name = disc.get('name', '').lower()
                            message = disc.get('message', '').lower()
                            if search_query.lower() in name or search_query.lower() in message:
                                disc['coursename'] = course['fullname']
                                disc['forumname'] = forum.get('name', 'Unknown')
                                matching_discussions.append(disc)

                                if len(matching_discussions) >= limit:
                                    break
                    except Exception:
                        continue

                if len(matching_discussions) >= limit:
                    break
            except Exception:
                continue

        if not matching_discussions:
            return f"No forum discussions found matching '{search_query}'."

        matching_discussions = matching_discussions[:limit]

        result = format_response(matching_discussions, f"Forum Search Results: '{search_query}'", format)

        return result
    except Exception as e:
        return f"Unable to search forums. Error: {str(e)}"

# ============================================================================
# WRITE OPERATIONS - Require write permission and course whitelist
# ============================================================================

@mcp.tool(
    name="moodle_create_forum_discussion",
    description="Create a new forum discussion/post. REQUIRED: course_id (integer), forum_id (integer), subject (string), message (string). Optional: pinned (boolean, default=False). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, forum_id=123, subject='New Topic', message='Discussion content'.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_create_forum_discussion(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    forum_id: int = Field(description="Forum ID where discussion will be created", gt=0),
    subject: str = Field(description="Discussion subject/title", min_length=1, max_length=255),
    message: str = Field(description="Discussion message content", min_length=1),
    pinned: bool = Field(default=False, description="Pin the discussion to top"),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Create a new discussion topic in a forum.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Args:
        course_id: Course ID (must be in whitelist!)
        forum_id: Forum ID where discussion will be created
        subject: Discussion subject/title
        message: Discussion message content
        pinned: Whether to pin the discussion
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with discussion ID

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Create a new discussion in forum 123 about homework"
        - "Post a new topic in the course forum"
        - "Start a discussion thread about the assignment"
    """
    moodle = get_moodle_client(ctx)

    # Prepare discussion data
    params = {
        'forumid': forum_id,
        'subject': subject,
        'message': message,
        'options[0][name]': 'discussionpinned',
        'options[0][value]': '1' if pinned else '0'
    }

    try:
        result = await moodle._make_request(
            'mod_forum_add_discussion',
            params
        )

        discussion_id = result.get('discussionid')

        if not discussion_id:
            return "Discussion created but no ID returned. It may have been created successfully."

        response_data = {
            'discussion_id': discussion_id,
            'forum_id': forum_id,
            'course_id': course_id,
            'subject': subject,
            'pinned': pinned
        }

        return format_response(response_data, "Forum Discussion Created", format)
    except Exception as e:
        raise Exception(f"Failed to create forum discussion: {str(e)}")

@mcp.tool(
    name="moodle_add_forum_post",
    description="Reply to an existing forum discussion post. REQUIRED: course_id (integer), post_id (integer), subject (string), message (string). WRITE OPERATION - only works on whitelisted courses (default: course 7299). Example: course_id=7299, post_id=456, subject='Re: Topic', message='Reply content'. Use moodle_get_discussion_posts to get post_id.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
@require_write_permission('course_id')
async def moodle_add_forum_post(
    course_id: int = Field(description="Course ID (must be whitelisted)", gt=0),
    post_id: int = Field(description="Post ID to reply to", gt=0),
    subject: str = Field(description="Reply subject/title", min_length=1, max_length=255),
    message: str = Field(description="Reply message content", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Add a reply to an existing forum discussion post.

    SAFETY: This write operation is only allowed on whitelisted courses.
    Default whitelist: [7299] (Elizabeth's Moodle Playground)

    Args:
        course_id: Course ID (must be in whitelist!)
        post_id: ID of the post to reply to
        subject: Reply subject/title
        message: Reply message content
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with new post ID

    Raises:
        WriteOperationError: If course_id is not whitelisted

    Example use cases:
        - "Reply to post 456 with a comment"
        - "Add a response to the discussion"
        - "Post a follow-up message"
    """
    moodle = get_moodle_client(ctx)

    # Prepare reply data
    params = {
        'postid': post_id,
        'subject': subject,
        'message': message,
        'options[0][name]': 'messageformat',
        'options[0][value]': '1'  # HTML format
    }

    try:
        result = await moodle._make_request(
            'mod_forum_add_discussion_post',
            params
        )

        new_post_id = result.get('postid')

        if not new_post_id:
            return "Reply created but no ID returned. It may have been posted successfully."

        response_data = {
            'new_post_id': new_post_id,
            'replied_to_post_id': post_id,
            'course_id': course_id,
            'subject': subject
        }

        return format_response(response_data, "Forum Reply Posted", format)
    except Exception as e:
        raise Exception(f"Failed to add forum post: {str(e)}")
