# Moodle MCP Setup - Windows Cheat Sheet

Quick setup guide for Windows users.

---

## Prerequisites

You'll need to install a few things first. Open **PowerShell as Administrator** (right-click → Run as Administrator).

### Install Git (if not already installed)
```powershell
winget install Git.Git
```
Close and reopen PowerShell after installing.

### Install Node.js (required for Gemini CLI)
```powershell
winget install OpenJS.NodeJS.LTS
```
Close and reopen PowerShell after installing.

### Install uv (Python package manager)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Close and reopen PowerShell after installing.

---

## Setup Steps

Open a **new PowerShell window** (regular, not Admin).

### 1. Download the project
```powershell
cd ~\Documents
git clone https://github.com/leshamblin/MoodleMCP.git
cd MoodleMCP
```

### 2. Install dependencies
```powershell
uv sync
```

### 3. Get a Moodle token
1. Log into Moodle
2. Click your name → **Preferences** → **Security keys**
3. Find **"Moodle mobile web service"** and copy the token
   - If no token exists, click to create one

### 4. Create the config file
```powershell
copy .env.example .env
```

Open `.env` in Notepad and add your details:
```powershell
notepad .env
```

Edit these lines:
```
MOODLE_DEV_URL=https://your-moodle-site.edu
MOODLE_DEV_TOKEN=paste_your_token_here
```

Save and close Notepad.

### 5. Install Gemini CLI
```powershell
npm install -g @google/gemini-cli
```

### 6. Add Moodle to Gemini CLI
```powershell
gemini mcp add --scope user moodle uv --directory $HOME\Documents\MoodleMCP run python -m moodle_mcp.main
```

### 7. Test it
```powershell
gemini "What Moodle courses am I enrolled in?"
```

---

## Troubleshooting

**"command not found" or "not recognized"**
- Close PowerShell and open a new one
- Make sure you installed the prerequisites above

**"Permission denied" errors**
- Run PowerShell as Administrator

**"gemini not recognized"**
- Run: `setx PATH "%PATH%;%AppData%\npm"` then restart PowerShell

**"Invalid token" error**
- Double-check your token in the `.env` file (no extra spaces)
- Make sure you copied the "Moodle mobile web service" token

**"Connection refused" error**
- Verify your Moodle URL is correct (include `https://`)
- Check that you can access the Moodle site in a browser

---

## Helpful Links

- [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/)
- [Gemini CLI Installation](https://geminicli.com/docs/get-started/installation/)
- [Node.js Download](https://nodejs.org/)
