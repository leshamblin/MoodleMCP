"""
Messaging and conversation tools - READ and WRITE operations.
"""

from pydantic import Field
from fastmcp import Context

from ..server import mcp
from ..utils.error_handling import handle_moodle_errors, require_write_permission
from ..utils.api_helpers import get_moodle_client
from ..utils.formatting import format_response
from ..models.base import ResponseFormat

@mcp.tool(
    name="moodle_get_conversations",
    description="Get message conversations for authenticated user. NO USER PARAMETERS REQUIRED - uses authenticated user automatically. Optional: limit (1-100, default=20), offset (default=0). Returns conversation IDs.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_conversations(
    limit: int = Field(default=20, description="Maximum conversations to return", ge=1, le=100),
    offset: int = Field(default=0, description="Offset for pagination", ge=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get list of message conversations for the current user.

    Returns recent conversations with unread counts and latest messages.

    Args:
        limit: Maximum number of conversations
        offset: Offset for pagination
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        List of conversations

    Example use cases:
        - "Show my messages"
        - "What conversations do I have?"
        - "List my recent messages"
    """
    moodle = get_moodle_client(ctx)

    # Get conversations
    try:
        conversations_data = await moodle._make_request(
            'core_message_get_conversations',
            {
                'userid': 0,  # 0 = current user
                'limitfrom': offset,
                'limitnum': limit
            }
        )

        conversations = conversations_data.get('conversations', [])

        if not conversations:
            return "No conversations found."

        return format_response(conversations, "Message Conversations", format)
    except Exception as e:
        return f"Unable to retrieve conversations. Error: {str(e)}"

@mcp.tool(
    name="moodle_get_messages",
    description="Get messages from a specific conversation. REQUIRED: conversation_id (integer). Optional: limit (1-100, default=20). Example: conversation_id=456. Use moodle_get_conversations to get conversation_id.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_messages(
    conversation_id: int = Field(description="Conversation ID", gt=0),
    limit: int = Field(default=20, description="Maximum messages to return", ge=1, le=100),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Get messages from a specific conversation.

    Returns message history for a conversation.

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Messages from the conversation

    Example use cases:
        - "Show messages from conversation 123"
        - "Get message history for conversation 45"
        - "Read messages in conversation 67"
    """
    moodle = get_moodle_client(ctx)

    try:
        messages_data = await moodle._make_request(
            'core_message_get_conversation_messages',
            {
                'currentuserid': 0,  # 0 = current user
                'convid': conversation_id,
                'limitfrom': 0,
                'limitnum': limit
            }
        )

        messages = messages_data.get('messages', [])

        if not messages:
            return f"No messages found in conversation {conversation_id}."

        return format_response(messages, f"Messages from Conversation {conversation_id}", format)
    except Exception as e:
        return f"Unable to retrieve messages from conversation {conversation_id}. Error: {str(e)}"

@mcp.tool(
    name="moodle_get_unread_count",
    description="Get count of unread messages for authenticated user. NO PARAMETERS REQUIRED. Returns simple integer count. Use this to check if there are new messages.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
@handle_moodle_errors
async def moodle_get_unread_count(
    ctx: Context = None
) -> str:
    """
    Get count of unread messages for the current user.

    Returns the total number of unread messages across all conversations.

    Args:
        ctx: FastMCP context

    Returns:
        Unread message count

    Example use cases:
        - "How many unread messages do I have?"
        - "Check my unread messages"
        - "Do I have new messages?"
    """
    moodle = get_moodle_client(ctx)

    try:
        unread_data = await moodle._make_request(
            'core_message_get_unread_conversations_count',
            {'userid': 0}  # 0 = current user
        )

        count = unread_data if isinstance(unread_data, int) else unread_data.get('count', 0)

        return f"You have **{count}** unread message(s)."
    except Exception as e:
        return f"Unable to retrieve unread message count. Error: {str(e)}"

# ============================================================================
# WRITE OPERATIONS - Messages are user-to-user, not course-specific
# ============================================================================

@mcp.tool(
    name="moodle_send_message",
    description="Send a private message to a user. REQUIRED: recipient_user_id (integer), message_text (string). WRITE OPERATION. Example: recipient_user_id=123, message_text='Hello!'.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
@handle_moodle_errors
async def moodle_send_message(
    recipient_user_id: int = Field(description="Recipient user ID", gt=0),
    message_text: str = Field(description="Message content", min_length=1),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Send a private message to a specific user.

    Messages are user-to-user communications and are not restricted
    by course whitelist.

    Args:
        recipient_user_id: ID of the user to send message to
        message_text: Message content to send
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message with message ID

    Example use cases:
        - "Send a message to user 123"
        - "Message user 456 about the assignment"
        - "Send a private message"
    """
    moodle = get_moodle_client(ctx)

    # Prepare message data
    params = {
        'messages[0][touserid]': recipient_user_id,
        'messages[0][text]': message_text,
        'messages[0][textformat]': 1  # HTML format
    }

    try:
        result = await moodle._make_request(
            'core_message_send_instant_messages',
            params
        )

        # Result is an array of message IDs
        if isinstance(result, list) and len(result) > 0:
            message_id = result[0].get('msgid')
        else:
            message_id = None

        if not message_id:
            return "Message sent but no ID returned. It may have been delivered successfully."

        response_data = {
            'message_id': message_id,
            'recipient_user_id': recipient_user_id,
            'message_sent': True
        }

        return format_response(response_data, "Message Sent", format)
    except Exception as e:
        raise Exception(f"Failed to send message: {str(e)}")

@mcp.tool(
    name="moodle_delete_conversation",
    description="Delete a conversation for the current user. REQUIRED: conversation_id (integer). WRITE OPERATION - DESTRUCTIVE. Example: conversation_id=789. Use moodle_get_conversations to get conversation_id. Note: Only deletes for current user, not other participants.",
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
@handle_moodle_errors
async def moodle_delete_conversation(
    conversation_id: int = Field(description="Conversation ID to delete", gt=0),
    format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format"),
    ctx: Context = None
) -> str:
    """
    Delete a conversation for the current user.

    NOTE: This only deletes the conversation for the authenticated user,
    not for other participants.

    Messages are user-to-user communications and are not restricted
    by course whitelist.

    Args:
        conversation_id: ID of the conversation to delete
        format: Output format (markdown or json)
        ctx: FastMCP context

    Returns:
        Confirmation message

    Example use cases:
        - "Delete conversation 789"
        - "Remove conversation with user X"
        - "Clear conversation history"
    """
    moodle = get_moodle_client(ctx)

    # Get current user ID
    site_info = await moodle.get_site_info()
    user_id = site_info['userid']

    # Prepare delete data
    params = {
        'userid': user_id,
        'conversationids[0]': conversation_id
    }

    try:
        result = await moodle._make_request(
            'core_message_delete_conversations_by_id',
            params
        )

        response_data = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'deleted': True
        }

        return format_response(response_data, "Conversation Deleted", format)
    except Exception as e:
        raise Exception(f"Failed to delete conversation: {str(e)}")
