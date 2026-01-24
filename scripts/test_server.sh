#!/bin/bash
source .venv/bin/activate
uv run fastmcp dev src/moodle_mcp/main.py &
SERVER_PID=$!
sleep 5
kill $SERVER_PID 2>/dev/null
echo "✓ Dev server started successfully"
