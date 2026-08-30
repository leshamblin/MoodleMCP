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

# MoodleMCP requires prod fields even in dev mode (pydantic validation)
export MOODLE_PROD_URL="${MOODLE_PROD_URL:-https://unused.example.com}"
export MOODLE_PROD_TOKEN="${MOODLE_PROD_TOKEN:-unused}"

# Ensure uv is on PATH (not available in non-interactive shells by default)
export PATH="$HOME/.local/bin:$PATH"

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

### `uv: not found`

Claude Code spawns MCP servers without loading shell profiles (`~/.bashrc`, `~/.profile`). If `uv` is installed in `~/.local/bin`, it won't be on PATH. The wrapper script above handles this with `export PATH="$HOME/.local/bin:$PATH"`.

### `ValidationError: prod_url Field required`

MoodleMCP's pydantic config requires `MOODLE_PROD_URL` and `MOODLE_PROD_TOKEN` even when `MOODLE_ENV=dev`. The wrapper script above sets placeholder values when they're not provided.

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
- **Server starts then crashes** — Run the wrapper script directly in a terminal to see the full error

---

*Contributed by the community | February 2026*
