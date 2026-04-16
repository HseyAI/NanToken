# NanToken - Intelligent LLM Token Tracker

A smart tool that tracks token usage, estimates costs, plans tasks, and works with ANY LLM.

## Features

- **Universal Support** - Works with ANY model (OpenAI, Claude, Gemini, Kimi, Qwen, DeepSeek, Llama, Ollama, etc.)
- **Slash Commands** - Simple `/ask`, `/estimate`, `/plan`, `/budget`
- **Inline Style** - Use `[prompt]` in scripts
- **Token Tracking** - One-line usage after every response
- **Task Planning** - Forecast tokens before complex tasks
- **Budget Guard** - Set limits, get warnings

## Quick Start

```bash
cd nantoken
pip install -r requirements.txt
python ask.py --setup
python ask.py /budget
```

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

## Usage

### First Time Setup
```bash
python ask.py --setup
```

### Slash Commands

```bash
# Ask LLM
ask /ask "write hello world in python"

# Estimate only
ask /estimate "create a website"

# Plan complex task
ask /plan "build rest api with auth"

# Check budget
ask /budget
```

### Inline Style (for scripts)

```bash
ask [write a function to reverse a string]
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

## Output Examples

```
[Ask] openai/gpt-4
Prompt: write hello world in python...
----------------------------------------
[Est] Input: 6 | Output: ~500 | Cost: ~$0.0151

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()

[Usage] OPENAI/gpt-4 | In: 6 | Out: 42 | Total: 48 | Cost: $0.0027
```

```
[Estimate] openai/gpt-4
==================================================
Prompt: build a rest api with auth...
Input:   6 tokens
Output:  ~500 tokens
Total:   ~506 tokens
Cost:    ~$0.0151

Daily budget: 0/100,000 (0.0%)
Remaining:    100,000 tokens
==================================================
```

## Configuration

Edit `nantoken.yaml`:

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
- requests, pyyaml, tiktoken, colorama, tabulate
- For specific providers: openai, anthropic, google-generativeai

## License

MIT