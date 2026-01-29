# Gemini CLI Setup Guide

*Version 0.24.0*

## 1. Authentication

Gemini CLI supports multiple authentication methods. Choose the one that fits your situation.

### Option A: Login with Google (Recommended for Organizations)

**Best for:** Users with a company, school, or Google Workspace account.

1. Run `gemini` in your terminal
2. Select **"Login with Google"**
3. Follow the browser-based login flow
4. If prompted, create or select a Google Cloud project

For organization accounts, you may need to:
- Create a Google Cloud project at [console.cloud.google.com](https://console.cloud.google.com)
- Enable the required APIs for your project

Credentials are cached locally for future sessions.

### Option B: Personal Google Account

**Best for:** Individual users with a personal Gmail account.

1. Run `gemini` in your terminal
2. Select **"Login with Google"**
3. Complete the browser-based authentication

If you have a Google AI Pro or Ultra subscription, use the associated account.

### Option C: Gemini API Key

**Best for:** AI Studio users or headless/automated environments.

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Create API key"**
3. Set the environment variable:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

4. Run `gemini` and select **"Use Gemini API key"**

### Option D: Vertex AI (Advanced)

**Best for:** Enterprise users with Google Cloud infrastructure.

Requires a Google Cloud project with Vertex AI API enabled.

**Using Application Default Credentials:**
```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

**Using Service Account (CI/CD):**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/keyfile.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

Run `gemini` and select **"Vertex AI"**.

### Persisting Environment Variables

Add variables to your shell config (`~/.zshrc` or `~/.bashrc`), or create a `~/.gemini/.env` file (automatically loaded by CLI).

---

## 2. Install Moodle MCP Integration

Connect your Moodle tool to the Gemini CLI so you can ask about your courses and gradebooks.

Run the following command (update the path to match your installation):

```bash
gemini mcp add moodle uv --directory /path/to/MoodleMCP run python -m moodle_mcp.main
```

**Example** (adjust for your system):

```bash
gemini mcp add moodle uv --directory /Users/leshamb2/Documents/Programming/MoodleMCP run python -m moodle_mcp.main
```

---

## 3. Core CLI Commands

The CLI can be used in several modes:

| Mode | Command | Description |
|------|---------|-------------|
| Interactive | `gemini` | Start a chat session |
| One-Shot | `gemini "Tell me about course ID 6292"` | Single prompt |
| YOLO Mode | `gemini -y` | Auto-accepts all tool calls (**use with caution!**) |
| Resume | `gemini --resume latest` | Continue previous session |

> **Pro Tip:** Use the `--model` flag to switch between different Gemini models. The flash models (especially `gemini-3-flash`) tend to work better with MCP tools.

### Enable Preview Features

To access the latest models, enable preview features in settings:

1. Run `gemini`
2. Type `/settings`
3. Set **"Preview Features (e.g., models)"** to `true`

This unlocks access to newer models like `gemini-3-flash` and `gemini-3-pro`.

---

## 4. Troubleshooting

- **Command not found:** Ensure your Python scripts folder is in your system `PATH`
- **Permission Denied:** Ensure you have granted "Web Service" permissions to your token in Moodle
- **MCP Server Error:** Check that the `--directory` path points to your MoodleMCP project root
- **Authentication Error:** Try running `gemini` again and re-authenticating, or check your API key/project settings

---

*Generated for NC State Moodle API Integration | January 2026*
