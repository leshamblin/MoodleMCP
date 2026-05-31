"""
Messaging and conversation tools - READ and WRITE operations.
"""

from dataclasses import dataclass, field
from typing import Annotated

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..server import mcp
from ..utils.error_handling import (
    handle_moodle_errors,
    require_global_write_permission,
)
from ..utils.api_helpers import get_moodle_client
from ..core.client import raise_on_row_errors


# --------------------------------------------------------------------------- #
# Local structured-output models (FastMCP 3.x).
# Kept here (not in models/results.py) since they're specific to message tools.
# --------------------------------------------------------------------------- #
@dataclass
class Conversation:
    id: int
    name: str | None = None
    type: int | None = None
    unreadcount: int | None = None


@dataclass
class ConversationList:
    conversations: list[Conversation] = field(default_factory=list)
    count: int = 0


@dataclass
class Message:
    id: int
    useridfrom: int | None = None
    text: str | None = None
    timecreated: int | None = None


@dataclass
class ConversationMessages:
    conversation_id: int
    messages: list[Message] = field(default_factory=list)
    count: int = 0


@dataclass
class UnreadCount:
    count: int


@dataclass
class SentMessage:
    message_id: int
    recipient_user_id: int
    message_sent: bool


@dataclass
class DeletedConversation:
    conversation_id: int
    user_id: int
    deleted: bool


@mcp.tool(
    name="moodle_get_conversations",
    description=(
        "Get message conversations for the authenticated user. NO USER PARAMETERS "
        "REQUIRED - uses the authenticated user automatically. Optional: limit "
        "(1-100, default=20), offset (default=0). Returns conversation IDs."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_conversations(
    limit: Annotated[
        int, Field(description="Maximum conversations to return", ge=1, le=100)
    ] = 20,
    offset: Annotated[
        int, Field(description="Offset for pagination", ge=0)
    ] = 0,
    ctx: Context = None,
) -> ConversationList:
    """List the current user's message conversations."""
    moodle = get_moodle_client(ctx)

    conversations_data = await moodle.call(
        "core_message_get_conversations",
        {
            "userid": 0,  # 0 = current user
            "limitfrom": offset,
            "limitnum": limit,
        },
    )

    conversations = [
        Conversation(
            id=c.get("id", 0),
            name=c.get("name"),
            type=c.get("type"),
            unreadcount=c.get("unreadcount"),
        )
        for c in (conversations_data or {}).get("conversations", [])
    ]
    return ConversationList(conversations=conversations, count=len(conversations))


@mcp.tool(
    name="moodle_get_messages",
    description=(
        "Get messages from a specific conversation. REQUIRED: conversation_id "
        "(integer). Optional: limit (1-100, default=20). Example: "
        "conversation_id=456. Use moodle_get_conversations to get conversation_id."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_messages(
    conversation_id: Annotated[int, Field(description="Conversation ID", gt=0)],
    limit: Annotated[
        int, Field(description="Maximum messages to return", ge=1, le=100)
    ] = 20,
    ctx: Context = None,
) -> ConversationMessages:
    """Get messages from a conversation."""
    moodle = get_moodle_client(ctx)

    messages_data = await moodle.call(
        "core_message_get_conversation_messages",
        {
            "currentuserid": 0,  # 0 = current user
            "convid": conversation_id,
            "limitfrom": 0,
            "limitnum": limit,
        },
    )

    messages = [
        Message(
            id=m.get("id", 0),
            useridfrom=m.get("useridfrom"),
            text=m.get("text"),
            timecreated=m.get("timecreated"),
        )
        for m in (messages_data or {}).get("messages", [])
    ]
    return ConversationMessages(
        conversation_id=conversation_id,
        messages=messages,
        count=len(messages),
    )


@mcp.tool(
    name="moodle_get_unread_count",
    description=(
        "Get the count of unread messages for the authenticated user. NO "
        "PARAMETERS REQUIRED. Returns a simple integer count. Use this to check "
        "if there are new messages."
    ),
    tags={"read"},
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False,
        idempotentHint=True, openWorldHint=True,
    ),
)
@handle_moodle_errors
async def moodle_get_unread_count(
    ctx: Context = None,
) -> UnreadCount:
    """Get the current user's unread message count."""
    moodle = get_moodle_client(ctx)

    # core_message_get_unread_conversations_count requires the recipient user
    # id under the key `useridto` (it does not accept 0 for "current user").
    info = await moodle.get_site_info()
    unread_data = await moodle.call(
        "core_message_get_unread_conversations_count",
        {"useridto": info["userid"]},
    )

    count = unread_data if isinstance(unread_data, int) else (unread_data or {}).get("count", 0)
    return UnreadCount(count=count)


# ============================================================================
# WRITE OPERATIONS - Messages are user-to-user, not course-specific
# ============================================================================

@mcp.tool(
    name="moodle_send_message",
    description=(
        "Send a private message to a user. REQUIRED: recipient_user_id (integer), "
        "message_text (string). WRITE OPERATION. Example: recipient_user_id=123, "
        "message_text='Hello!'."
    ),
    tags={"write", "message"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=False,
        idempotentHint=False, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_global_write_permission
async def moodle_send_message(
    recipient_user_id: Annotated[
        int, Field(description="Recipient user ID", gt=0)
    ],
    message_text: Annotated[
        str, Field(description="Message content", min_length=1)
    ],
    ctx: Context = None,
) -> SentMessage:
    """Send a private message to a user.

    User-to-user messaging is not restricted by the course whitelist.
    """
    moodle = get_moodle_client(ctx)

    params = {
        "messages[0][touserid]": recipient_user_id,
        "messages[0][text]": message_text,
        "messages[0][textformat]": 1,  # HTML format
    }

    result = await moodle.call("core_message_send_instant_messages", params)

    # core_message_send_instant_messages returns a list of per-message results
    # that may carry 'errormessage' without raising; surface those as errors.
    raise_on_row_errors(result)

    message_id = result[0].get("msgid")

    return SentMessage(
        message_id=message_id,
        recipient_user_id=recipient_user_id,
        message_sent=True,
    )


@mcp.tool(
    name="moodle_delete_conversation",
    description=(
        "Delete a conversation for the current user. REQUIRED: conversation_id "
        "(integer). WRITE OPERATION - DESTRUCTIVE. Example: conversation_id=789. "
        "Use moodle_get_conversations to get conversation_id. Note: Only deletes "
        "for the current user, not other participants."
    ),
    tags={"write", "message"},
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True,
        idempotentHint=True, openWorldHint=False,
    ),
)
@handle_moodle_errors
@require_global_write_permission
async def moodle_delete_conversation(
    conversation_id: Annotated[
        int, Field(description="Conversation ID to delete", gt=0)
    ],
    ctx: Context = None,
) -> DeletedConversation:
    """Delete a conversation for the current user.

    User-to-user messaging is not restricted by the course whitelist.
    """
    moodle = get_moodle_client(ctx)

    site_info = await moodle.get_site_info()
    user_id = site_info["userid"]

    params = {
        "userid": user_id,
        "conversationids[0]": conversation_id,
    }

    await moodle.call("core_message_delete_conversations_by_id", params)

    return DeletedConversation(
        conversation_id=conversation_id,
        user_id=user_id,
        deleted=True,
    )
