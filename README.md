# Moodle MCP Server

Connect University approved AI assistants like Gemini to your Moodle courses.

This server lets AI tools read your course information, grades, assignments, messages, and more directly from Moodle. It can also perform actions like sending messages, creating calendar events, and posting to forums (with safety protections).

## What You Can Do

Once connected, your AI assistant can help you:

- **View courses** - List your enrolled courses and their contents
- **Check grades** - See grades for yourself or your students
- **Manage assignments** - View submissions, due dates, and grading status
- **Read messages** - Access conversations and unread message counts
- **Check calendar** - See upcoming events and deadlines
- **Browse forums** - Read discussions and search forum content
- **View groups** - See group memberships and members

With write permissions enabled, the AI can also:
- Send messages to students
- Create calendar events
- Post forum discussions and replies
- Grade assignments
- Manage enrollments

## Quick Start

### 1. Get Your Moodle Token

1. Log in to your Moodle site
2. Go to **Profile** (click your name) > **Preferences** > **Security keys**
3. Create a new token or copy an existing one
4. Save this token somewhere safe - you'll need it in step 3

### 2. Download This Project

Download or clone this folder to your computer. Remember where you put it.

### 3. Create Your Configuration File

1. Find the file called `.env.example` in the project folder
2. Make a copy and rename it to `.env`
3. Open `.env` in a text editor and fill in your details:

```bash
# Your Moodle site URL (no trailing slash)
MOODLE_DEV_URL=https://your-moodle-site.edu

# Your token from step 1
MOODLE_DEV_TOKEN=paste_your_token_here

# Leave these as-is for safety
MOODLE_DEV_COURSE_WHITELIST=7299
MOODLE_PROD_ALLOW_WRITES=false
```

### 4. Connect to Gemini CLI

See the [Gemini CLI MCP Setup Guide](Gemini_CLI_Setup_Guide.md) for detailed instructions on connecting this server to Gemini CLI.

---

## Testing Your Connection

Once connected, try asking your AI assistant:

> "What Moodle courses am I enrolled in?"

or

> "Show me my recent grades"

If it works, you'll see your actual course data.

---

## Troubleshooting

### "Module not found" error
Make sure Python 3.10+ is installed and the PYTHONPATH points to the `src` folder inside MoodleAPI.

### "Invalid token" error
1. Check that your token is correct in the `.env` file
2. Make sure there are no extra spaces around the token
3. Verify the token hasn't expired in Moodle

### "Connection refused" error
1. Verify your Moodle URL is correct (include `https://`)
2. Check that you can access the Moodle site in a browser
3. Make sure Web Services are enabled on your Moodle instance

### AI tool doesn't show Moodle
1. Make sure you saved the config file
2. Restart your AI tool completely
3. Check that the file path is correct for your computer

---

## Write Operation Safety

By default, the server only allows read operations. This protects your Moodle data from accidental changes.

To enable write operations (sending messages, creating events, etc.):

1. Open your `.env` file
2. Find `MOODLE_DEV_COURSE_WHITELIST`
3. Add your course IDs, separated by commas:

```bash
MOODLE_DEV_COURSE_WHITELIST=7299,12345,67890
```

Only courses in this list will allow write operations. This keeps you safe while still letting you use write features in specific courses.

---

## Requirements

- Python 3.10 or higher
- A Moodle account with Web Services access
- Gemini CLI

### Installing Python Dependencies

If you get import errors, install the required packages:

```bash
pip install fastmcp httpx pydantic pydantic-settings python-dotenv
```

Or if you have `uv` installed:

```bash
cd /path/to/MoodleAPI
uv sync
```

---

## Available Tools

The server provides 68 tools organized by category:

| Category | Tools | Description |
|----------|-------|-------------|
| Site | 3 | Connection info and available functions |
| Courses | 7 | List courses, contents, participants |
| Users | 5 | User profiles and search |
| Grades | 8 | View and update grades |
| Assignments | 7 | View and submit assignments |
| Messages | 5 | Read and send messages |
| Calendar | 5 | View and create events |
| Forums | 5 | Read and post discussions |
| Groups | 9 | View and manage groups |
| Enrollment | 2 | Enroll and unenroll users |
| Quizzes | 5 | View and take quizzes |
| Completion | 4 | Track activity completion |
| Badges | 2 | View earned badges |

---

## Getting Help

If you run into issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Make sure your `.env` file has the correct values
3. Verify Python is installed: `python3 --version`
4. Check that you can access your Moodle site normally

---

## Security Notes

- Your Moodle token is stored only in your local `.env` file
- Never share your `.env` file or commit it to version control
- The `.env` file is automatically ignored by git
- Write operations require explicit course whitelisting
- Production environments block all writes by default

---

Built with [FastMCP](https://gofastmcp.com) for the [Model Context Protocol](https://modelcontextprotocol.io)
