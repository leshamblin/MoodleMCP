# Dual Moodle Instance Setup

You now have access to TWO Moodle instances with valid tokens:

## Instance 1: Moodle Courses
- **URL:** https://moodle-courses2527.wolfware.ncsu.edu
- **Version:** 2024100706.03
- **User:** Elizabeth Shamblin (leshamb2@ncsu.edu, ID: 624)
- **Courses:** 7 courses
- **Token:** (stored in .env)

## Instance 2: Moodle Projects
- **URL:** https://moodle-projects.wolfware.ncsu.edu
- **Version:** 4.5.6+ (Build: 20250822)
- **User:** Elizabeth Shamblin (leshamb2@ncsu.edu, ID: 247714)
- **Courses:** 10+ courses
- **Token:** REDACTED_DEV_TOKEN

---

## Option 1: Single Instance (Switch Between)

**Current setup** - Edit `.env` to switch:

```bash
# For Moodle Courses
MOODLE_URL=https://moodle-courses2527.wolfware.ncsu.edu
MOODLE_TOKEN=your_courses_token

# OR for Moodle Projects
MOODLE_URL=https://moodle-projects.wolfware.ncsu.edu
MOODLE_TOKEN=REDACTED_DEV_TOKEN
```

**Pros:**
- Simple configuration
- Easy to switch

**Cons:**
- Can only access one instance at a time
- Need to restart Claude Desktop when switching

---

## Option 2: Dual MCP Servers (Recommended)

**Claude Desktop Config** - Access both simultaneously:

```json
{
  "mcpServers": {
    "moodle-courses": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/leshamb2/Documents/Programming/MoodleMCP",
        "run",
        "python",
        "-m",
        "moodle_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "/Users/leshamb2/Documents/Programming/MoodleMCP/src",
        "MOODLE_URL": "https://moodle-courses2527.wolfware.ncsu.edu",
        "MOODLE_TOKEN": "your_courses_token_here"
      }
    },
    "moodle-projects": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/leshamb2/Documents/Programming/MoodleMCP",
        "run",
        "python",
        "-m",
        "moodle_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "/Users/leshamb2/Documents/Programming/MoodleMCP/src",
        "MOODLE_URL": "https://moodle-projects.wolfware.ncsu.edu",
        "MOODLE_TOKEN": "REDACTED_DEV_TOKEN"
      }
    }
  }
}
```

**Pros:**
- Access both instances simultaneously
- Tools will be prefixed: `moodle-courses__moodle_get_course_details` and `moodle-projects__moodle_get_course_details`
- No need to restart to switch

**Cons:**
- 80 tools total (40 × 2)
- Slightly more complex configuration

---

## Option 3: Separate Project Folders

Create two separate installations:

```bash
# Instance 1
/Users/leshamb2/Documents/Programming/MoodleMCP-Courses/
  .env -> MOODLE_URL=moodle-courses2527...

# Instance 2
/Users/leshamb2/Documents/Programming/MoodleMCP-Projects/
  .env -> MOODLE_URL=moodle-projects...
```

**Pros:**
- Complete separation
- Different versions/configurations possible
- Clear naming in Claude Desktop

**Cons:**
- Code duplication
- Need to maintain two codebases

---

## Recommended Setup

**Use Option 2 (Dual MCP Servers)** with the configuration above.

### Steps:

1. **Keep your current `.env`** for the courses instance
2. **Edit Claude Desktop config:**
   ```bash
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
3. **Add both servers** using the JSON above
4. **Restart Claude Desktop**

You'll then be able to:
- Query courses instance: "List my courses" (will show tools from both)
- Query projects instance: Same tools, different data
- Claude will show you which server it's using

---

## Testing Both Instances

After setup, test with:

```
"How many courses do I have on moodle-courses?"
"How many courses do I have on moodle-projects?"
"What groups exist in course 2292 on moodle-courses?"
"What groups exist in course 13043 on moodle-projects?"
```

---

## Security Note

⚠️ **IMPORTANT:** I noticed you shared a token in the conversation. Consider:

1. **Regenerating the token** in Moodle after we're done testing
2. **Never commit tokens** to git (`.env` is already in `.gitignore`)
3. **Use environment variables** for sensitive data

---

Would you like me to help you set up Option 2 (Dual MCP Servers)?
