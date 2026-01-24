# DEV/PROD Environment Configuration

**Date:** 2025-10-26
**Feature:** Separate development and production Moodle instances

---

## Overview

The MCP server now supports **separate DEV and PROD environments** with automatic selection based on configuration.

**DEV instance is used by default for ALL development work.**

---

## Your Instances

### Development (DEV) - **DEFAULT**
- **URL:** https://moodle-projects.wolfware.ncsu.edu
- **Version:** 4.5.6+ (Build: 20250822)
- **Purpose:** Testing, development, course projects
- **Courses:** 10+ courses including development/sandbox courses
- **User ID:** 247714

### Production (PROD)
- **URL:** https://moodle-courses2527.wolfware.ncsu.edu
- **Version:** 4.5.6+ (Build: 20250822)
- **Purpose:** Live teaching courses (2025-2027)
- **Courses:** 7 active teaching courses
- **User ID:** 624

---

## Configuration

### Environment Variables (.env)

```bash
# Development instance (DEFAULT)
MOODLE_DEV_URL=https://moodle-projects.wolfware.ncsu.edu
MOODLE_DEV_TOKEN=REDACTED_DEV_TOKEN

# Production instance
MOODLE_PROD_URL=https://moodle-courses2527.wolfware.ncsu.edu
MOODLE_PROD_TOKEN=REDACTED_PROD_TOKEN

# Environment selection (defaults to 'dev' if not set)
# MOODLE_ENV=dev
```

### How It Works

The `MoodleConfig` class now has:

1. **Separate DEV/PROD fields:**
   - `dev_url` / `dev_token`
   - `prod_url` / `prod_token`

2. **Environment selector:**
   - `env` field (defaults to `'dev'`)
   - Set via `MOODLE_ENV` environment variable

3. **Smart properties:**
   - `config.url` - Returns DEV or PROD URL based on `env`
   - `config.token` - Returns DEV or PROD token based on `env`
   - `config.environment_name` - Returns "DEVELOPMENT" or "PRODUCTION"

---

## Usage

### Default Behavior (DEV)

**All commands use DEV by default:**

```bash
# Testing
python test_connection.py
# → Uses DEVELOPMENT instance

# Development server
fastmcp dev src/moodle_mcp/main.py
# → Connects to DEVELOPMENT instance

# Running tests
pytest
# → Tests against DEVELOPMENT instance
```

### Using Production

**Explicitly set MOODLE_ENV=prod:**

```bash
# Testing PROD
MOODLE_ENV=prod python test_connection.py
# → Uses PRODUCTION instance

# Run against PROD (careful!)
MOODLE_ENV=prod fastmcp dev src/moodle_mcp/main.py
# → Connects to PRODUCTION instance
```

---

## Testing Both Instances

### Quick Test Script

```bash
# Test DEV (default)
python test_connection.py

# Test PROD
MOODLE_ENV=prod python test_connection.py
```

### Expected Output

**DEV:**
```
Testing DEVELOPMENT environment
URL: https://moodle-projects.wolfware.ncsu.edu
============================================================
✅ CONNECTION SUCCESSFUL!

Site Name: Moodle Projects
Moodle Version: 4.5.6+ (Build: 20250822)
Username: leshamb2@ncsu.edu
User ID: 247714
Full Name: Elizabeth Shamblin

Available Functions: 450
Group-related functions: 12
```

**PROD:**
```
Testing PRODUCTION environment
URL: https://moodle-courses2527.wolfware.ncsu.edu
============================================================
✅ CONNECTION SUCCESSFUL!

Site Name: Moodle Courses 2025-2027
Moodle Version: 4.5.6+ (Build: 20250822)
Username: leshamb2@ncsu.edu
User ID: 624
Full Name: Elizabeth Shamblin

Available Functions: 450
Group-related functions: 12
```

---

## Claude Desktop Integration

### Single Instance (DEV by default)

```json
{
  "mcpServers": {
    "moodle": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/wjs/Documents/Programming/MoodleAPI",
        "run",
        "python",
        "-m",
        "moodle_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "/Users/wjs/Documents/Programming/MoodleAPI/src"
      }
    }
  }
}
```

**Note:** This uses `.env` file, which defaults to DEV.

### Dual Instances (Both Available)

```json
{
  "mcpServers": {
    "moodle-dev": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/wjs/Documents/Programming/MoodleAPI",
        "run",
        "python",
        "-m",
        "moodle_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "/Users/wjs/Documents/Programming/MoodleAPI/src",
        "MOODLE_ENV": "dev"
      }
    },
    "moodle-prod": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/wjs/Documents/Programming/MoodleAPI",
        "run",
        "python",
        "-m",
        "moodle_mcp.main"
      ],
      "env": {
        "PYTHONPATH": "/Users/wjs/Documents/Programming/MoodleAPI/src",
        "MOODLE_ENV": "prod"
      }
    }
  }
}
```

**Note:** Tokens are loaded from `.env` file automatically.

---

## Implementation Details

### Files Modified

#### 1. `src/moodle_mcp/core/config.py`
- Added `dev_url`, `dev_token`, `prod_url`, `prod_token` fields
- Added `env` field with default `'dev'`
- Added `url` and `token` properties that select based on `env`
- Added `environment_name` property for logging

#### 2. `src/moodle_mcp/main.py`
- Updated startup logging to show environment name
- Now displays: `Environment: DEVELOPMENT` or `Environment: PRODUCTION`

#### 3. `.env` file
- Updated with DEV and PROD URLs/tokens
- Removed old `MOODLE_URL` and `MOODLE_TOKEN` variables

#### 4. `.env.example`
- Complete rewrite with DEV/PROD structure
- Clear documentation of environment selection
- Removed unused configuration options

#### 5. `test_connection.py` (renamed from `test_projects_connection.py`)
- Now supports DEV/PROD testing via `MOODLE_ENV`
- Can still test custom URL/token pairs
- Shows environment name in output

#### 6. `README.md`
- Updated configuration section
- Added environment switching examples
- Clarified token generation instructions

---

## Best Practices

### Development Work

✅ **DO:**
- Use DEV instance for all testing and development
- Test new features on DEV first
- Use DEV for experimenting with API calls
- Use DEV for automated tests

❌ **DON'T:**
- Run untested code against PROD
- Use PROD for development/debugging
- Commit changes without testing on DEV first

### Production Use

✅ **DO:**
- Only use PROD for verified, working code
- Test thoroughly on DEV before PROD
- Be cautious with PROD data
- Document when you use PROD

❌ **DON'T:**
- Use PROD as a testing ground
- Run experimental code on PROD
- Assume DEV and PROD are identical

---

## Safety Features

1. **DEV is default** - You have to explicitly set `MOODLE_ENV=prod`
2. **Environment logging** - Server startup shows which environment is active
3. **Separate tokens** - DEV and PROD use different authentication
4. **Clear naming** - "DEVELOPMENT" vs "PRODUCTION" in all logs

---

## Migration from Old Config

### Old .env (Single Instance)
```bash
MOODLE_URL=https://moodle.example.com
MOODLE_TOKEN=your_token
```

### New .env (DEV/PROD)
```bash
MOODLE_DEV_URL=https://moodle-dev.example.com
MOODLE_DEV_TOKEN=your_dev_token
MOODLE_PROD_URL=https://moodle-prod.example.com
MOODLE_PROD_TOKEN=your_prod_token
# MOODLE_ENV=dev  # Optional, defaults to dev
```

**Old code continues to work** because `config.url` and `config.token` properties maintain compatibility.

---

## Verification

Both instances verified working:

✅ **DEV (moodle-projects):**
- Connection successful
- 450 functions available
- 12 group functions
- 10+ courses accessible

✅ **PROD (moodle-courses2527):**
- Connection successful
- 450 functions available
- 12 group functions
- 7 courses accessible

---

## Summary

**Default behavior:** Everything uses DEVELOPMENT instance

**To use production:** Set `MOODLE_ENV=prod` environment variable

**Both instances are the same Moodle version (4.5.6+) with identical API capabilities**

The main difference is the **data**:
- DEV = Projects, experiments, development work
- PROD = Live teaching courses (2025-2027)

---

**All development work should use DEV instance by default! ✅**
