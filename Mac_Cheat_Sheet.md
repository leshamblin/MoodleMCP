# Moodle MCP Setup - Mac Cheat Sheet

Quick setup guide for Mac users with Homebrew installed.

---

## 1. Install uv (Python package manager)
```bash
brew install uv
```

## 2. Download the project
```bash
cd ~/Documents
git clone https://github.com/leshamblin/MoodleMCP.git
cd MoodleMCP
```

## 3. Install dependencies
```bash
uv sync
```

## 4. Get a Moodle token
1. Log into Moodle
2. Click your name → **Preferences** → **Security keys**
3. Find **"Moodle mobile web service"** and copy the token
   - If no token exists, click to create one

## 5. Create the config file
```bash
cp .env.example .env
```

Open `.env` in a text editor (TextEdit, VS Code, etc.) and add your details:
```bash
MOODLE_DEV_URL=https://your-moodle-site.edu
MOODLE_DEV_TOKEN=paste_your_token_here
```

## 6. Add to Gemini CLI
```bash
gemini mcp add --scope user moodle uv --directory ~/Documents/MoodleMCP run python -m moodle_mcp.main
```

## 7. Test it
```bash
gemini "What Moodle courses am I enrolled in?"
```

---

## Troubleshooting

**"command not found: gemini"**
- Install Gemini CLI first: https://github.com/google-gemini/gemini-cli

**"command not found: git"**
- Install git: `brew install git`

**"Invalid token" error**
- Double-check your token in the `.env` file (no extra spaces)
- Make sure you copied the "Moodle mobile web service" token

**"Connection refused" error**
- Verify your Moodle URL is correct (include `https://`)
- Check that you can access the Moodle site in a browser
