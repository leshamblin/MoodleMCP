# Claude Code Setup Guide

Connect MoodleMCP to [Claude Code](https://docs.anthropic.com/en/docs/claude-code) so you can ask about your courses, grades, assignments, and more.

## Prerequisites

- Claude Code installed and working
- MoodleMCP cloned and dependencies installed (`uv sync`)
- A Moodle token (see [main README](README.md#1-get-your-moodle-token))

## 1. Configure Environment Variables

Make sure your `.env` file is set up in the MoodleMCP project root:

```bash
cd /path/to/MoodleMCP
cp .env.example .env
```

Edit `.env` with your Moodle credentials:

```bash
MOODLE_DEV_URL=https://your-moodle-site.edu
MOODLE_DEV_TOKEN=your_token_here
MOODLE_ENV=dev
```

## 2. Create a Wrapper Script

Claude Code's `.mcp.json` resolves `${VAR}` syntax from the **shell environment**, not from `.env` files. This means environment variables defined only in `.env` won't be available to the MCP server when launched by Claude Code.

The simplest solution is a wrapper script that sources `.env` before starting the server.

Create `scripts/start-moodle-mcp.sh` in your project (or wherever you prefer):

```bash
#!/usr/bin/env bash
# Wrapper script for MoodleMCP — sources .env before starting the server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env from project root
if [[ -f "$PROJECT_DIR/.env" ]]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
else
  echo "Error: $PROJECT_DIR/.env not found" >&2
  exit 1
fi

exec uv --directory "$PROJECT_DIR" run moodle-mcp
```

Make it executable:

```bash
chmod +x scripts/start-moodle-mcp.sh
```

## 3. Add MCP Configuration

Create or edit `.mcp.json` in your project directory (or `~/.claude/settings.json` for global config):

```json
{
  "mcpServers": {
    "moodle": {
      "command": "/absolute/path/to/MoodleMCP/scripts/start-moodle-mcp.sh",
      "args": []
    }
  }
}
```

> **Important:** Use an absolute path to the wrapper script. Relative paths may not resolve correctly.

## 4. Verify the Connection

Start Claude Code in a directory with the `.mcp.json`, then ask:

> "What Moodle courses am I enrolled in?"

If the connection is working, you'll see your course data.

## Common Pitfalls

### Entry point is `moodle-mcp`, not `mcp-server-moodle`

The correct command to start the server is:

```bash
uv --directory /path/to/MoodleMCP run moodle-mcp
```

This matches the entry point defined in `pyproject.toml`. Using `mcp-server-moodle` will fail with a "command not found" error.

### Environment variables not reaching the server

If you configure `.mcp.json` like this, the variables will **not** resolve:

```json
{
  "mcpServers": {
    "moodle": {
      "command": "uv",
      "args": ["--directory", "/path/to/MoodleMCP", "run", "moodle-mcp"],
      "env": {
        "MOODLE_DEV_URL": "${MOODLE_URL}",
        "MOODLE_DEV_TOKEN": "${MOODLE_TOKEN}"
      }
    }
  }
}
```

Claude Code resolves `${VAR}` from the shell environment at launch time, not from `.env` files. Use the wrapper script approach from Step 2 instead.

### Permission denied

Make sure the wrapper script is executable:

```bash
chmod +x scripts/start-moodle-mcp.sh
```

## Troubleshooting

- **"No MCP servers configured"** — Check that `.mcp.json` is in your working directory or `~/.claude/settings.json`
- **"Connection refused"** — Verify your Moodle URL is correct and accessible
- **"Invalid token"** — Check the token in your `.env` file, ensure no extra whitespace
- **Server starts but no tools appear** — Restart Claude Code after changing `.mcp.json`

---

*Contributed by the community | February 2026*
