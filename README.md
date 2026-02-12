# Terminal Helper AI

A local AI agent that helps you use the Windows or Linux terminal. Ask in natural language, get appropriate commands with descriptions and prerequisites, and execute them only when you give permission. Includes an update scanner to find outdated packages installed via terminal.

## Features

- **Natural language input** — Describe what you want to do; the AI suggests the right commands
- **Descriptions & prerequisites** — Each suggestion includes a short description and any prerequisites
- **Permission-based execution** — Commands run only after you click "Execute Command(s)"
- **Update scanner** — Scans winget (Windows), apt (Linux), pip (Python) for outdated packages
- **One-click updates** — Update all detected packages with your permission

## Requirements

- Python 3.10+
- [OpenRouter API key](https://openrouter.ai/keys) (primary; OpenAI also supported)

## Setup

1. **Clone or download** this project.

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure OpenRouter**:

   - Copy `.env.example` to `.env` (or use the existing `.env`)
   - Replace `__YOUR_OPENROUTER_KEY_HERE__` with your [OpenRouter API key](https://openrouter.ai/keys)
   - Replace `__YOUR_MODEL_HERE__` with your model (e.g. `tngtech/deepseek-r1t2-chimera:free`)

   ```env
   OPENROUTER_API_KEY=sk-or-your-actual-key
   OPENAI_MODEL=tngtech/deepseek-r1t2-chimera:free
   ```

## Run

```bash
python app.py
```

## Usage

### Commands tab

1. Type what you want to do in natural language (e.g. "list all files in the current directory", "create a new git branch called feature-x").
2. The AI returns one or more commands with a description and prerequisites.
3. Review the suggestions.
4. Click **Execute Command(s)** to run them (only when you're ready).

### Updates tab

1. Click **Scan for Updates** to check for outdated packages (winget, pip, apt).
2. Review the list of packages with available updates.
3. Click **Update All** to apply updates when you give permission.

**Note:** On Linux, `apt` updates may require `sudo`; you might be prompted for your password.

## Environment variables

| Variable             | Description                              | Example                            |
|----------------------|------------------------------------------|------------------------------------|
| `OPENROUTER_API_KEY` | OpenRouter API key (primary)             | Get at https://openrouter.ai/keys  |
| `OPENAI_MODEL`       | Model to use (required)                  | `tngtech/deepseek-r1t2-chimera:free`  |
| `OPENAI_API_KEY`     | Optional OpenAI key (fallback)           | `sk-...`                           |
| `OPENAI_BASE_URL`    | Custom API base URL (defaults to OpenRouter) | `https://openrouter.ai/api/v1`  |

## Supported package managers

| OS      | Package manager | Scan | Update |
|---------|-----------------|------|--------|
| Windows | winget          | ✓    | ✓      |
| Windows | pip             | ✓    | ✓      |
| Windows | npm             | ✓    | ✓      |
| Linux   | apt             | ✓    | ✓      |
| Linux   | pip             | ✓    | ✓      |

## Security

- Commands are never executed automatically; you must click the execute button.
- Your `.env` file (with API keys) is in `.gitignore` and should not be committed.
- Updates run only after you click "Update All".
