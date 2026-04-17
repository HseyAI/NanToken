# NanToken - Intelligent LLM Token Tracker

A smart tool that tracks token usage, estimates costs, plans tasks, and works with ANY LLM — right inside your AI coding terminal.

## What It Does

NanToken runs as an **MCP plugin** inside Claude Code, Cursor, Windsurf, and any MCP-compatible editor. No context switching — get token stats, budget alerts, and cost estimates where you code.

**9 MCP Tools:**
| Tool | What It Does |
|------|-------------|
| `token_estimate` | Estimate tokens and cost before sending a prompt |
| `token_track` | Record token usage from any LLM call |
| `token_budget` | Check daily/monthly budget status |
| `token_stats` | Usage analytics for the past N days |
| `token_plan` | Break a task into steps with per-step cost forecasts |
| `token_compare` | Compare cost across multiple models side-by-side |
| `token_history` | Per-project usage history and breakdown |
| `token_cache_stats` | Semantic cache health |
| `token_session` | Current session summary (auto-tracked or manual) |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/HseyAI/NanToken.git
cd NanToken
pip install -r requirements.txt
```

### 2. Setup config

```bash
python ask.py --setup
```

This creates `smartllm.yaml` with your provider, API key, model, and budget settings.

### 3. Connect to your editor

**Option A: Per-project (tools available only in the NanToken folder)**

The `.mcp.json` is already in the repo. Just open the NanToken folder in Claude Code or Cursor — the tools appear automatically.

**Option B: Global (tools available in every project — recommended)**

Add NanToken to your editor's global config:

**Claude Code** — add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "nantoken": {
      "command": "python",
      "args": ["-m", "nantoken"],
      "cwd": "/path/to/NanToken",
      "env": {
        "NANTOKEN_CONFIG": "/path/to/NanToken/smartllm.yaml"
      }
    }
  }
}
```

**Cursor** — add to `.cursor/mcp.json` or global settings:
```json
{
  "mcpServers": {
    "nantoken": {
      "command": "python",
      "args": ["-m", "nantoken"],
      "cwd": "/path/to/NanToken",
      "env": {
        "NANTOKEN_CONFIG": "/path/to/NanToken/smartllm.yaml"
      }
    }
  }
}
```

**Windsurf / Other MCP editors** — same format, check your editor's MCP docs for the config file location.

> Replace `/path/to/NanToken` with the actual path where you cloned the repo.

### 4. Enable auto-tracking (recommended)

Auto-tracking captures **real token usage** from every Claude response — no manual tracking needed.

```bash
python -m nantoken.hooks.install
```

This adds a Claude Code hook that reads actual token counts from your session transcript. Usage data is stored in `~/.nantoken/`.

**Manual setup:** Add this to `~/.claude/settings.json`:
```json
{
  "hooks": {
    "Stop": [
      {
        "type": "command",
        "command": "python \"/path/to/NanToken/nantoken/hooks/stop_track.py\""
      }
    ]
  }
}
```

### 5. Restart your editor

The NanToken tools will now appear. Try:
- *"Check my token budget"* — calls `token_budget`
- *"Compare cost of this prompt across models"* — calls `token_compare`
- *"Show my usage by project this week"* — calls `token_history`
- `/token` — quick dashboard (if skill is installed)

### 6. Install /token slash command (optional)

Copy the skill to your global Claude Code skills:

```bash
# Linux/macOS
cp -r .claude/skills/token ~/.claude/skills/token

# Windows
xcopy .claude\skills\token %USERPROFILE%\.claude\skills\token\ /E /I
```

Then type `/token` in any project for a quick usage dashboard.

## Supported Models

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4, gpt-4o, gpt-3.5-turbo |
| Anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| Google | gemini-pro, gemini-1.5-flash |
| Moonshot | kimi, kimi-k2 |
| Qwen | qwen-turbo, qwen-plus, qwen-max |
| DeepSeek | deepseek-chat, deepseek-coder |
| Meta | llama-3-70b, llama-3-8b |
| Local | ollama, lmstudio, any OpenAI-compatible |

## Standalone CLI (Optional)

NanToken also works as a standalone CLI if you prefer:

```bash
# Ask LLM with tracking
python ask.py /ask "write hello world in python"

# Estimate cost only
python ask.py /estimate "create a website"

# Plan a complex task
python ask.py /plan "build rest api with auth"

# Check budget
python ask.py /budget
```

### Inline Style (for scripts)

```bash
python ask.py [write a function to reverse a string]
```

### Use in Your Code

```python
from nantoken.integrate import smart_ask, smart_estimate, smart_track

# Ask with tracking
response, usage = smart_ask("write a function")

# Estimate without calling
est = smart_estimate("create a website")
print(f"Cost: ${est['estimated_cost']:.4f}")

# Track any LLM call
smart_track(input_tokens=100, output_tokens=500, model="gpt-4")
```

## Configuration

Edit `smartllm.yaml` (created by `python ask.py --setup`):

```yaml
llm_provider: openai
model: gpt-4
api_key: YOUR_KEY
endpoint: ""  # For custom/local APIs

budget:
  daily_limit: 100000
  monthly_limit: 3000000

# Add your model pricing
pricing:
  model_pricing:
    gpt-4: {input: 0.03, output: 0.06}
    kimi: {input: 0.01, output: 0.03}
    qwen-turbo: {input: 0.002, output: 0.006}
```

## Requirements

- Python 3.9+
- Core: tiktoken, pyyaml, requests, mcp[cli]
- Optional (for direct LLM calls): openai, anthropic, google-generativeai

## License

MIT
