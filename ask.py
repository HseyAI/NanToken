#!/usr/bin/env python3
"""
NanToken Interactive Setup - First run wizard
"""

import os
import sys

def first_time_setup():
    """Ask user for API key directly."""
    print("\n" + "=" * 50)
    print("NanToken - First Time Setup")
    print("=" * 50)
    
    print("\nWhich LLM provider do you want to use?")
    print("  1. OpenAI (GPT-4, GPT-4o)")
    print("  2. Anthropic (Claude)")
    print("  3. Google (Gemini)")
    print("  4. Kimi (Moonshot)")
    print("  5. Qwen (Alibaba)")
    print("  6. DeepSeek")
    print("  7. Ollama (local)")
    print("  8. Custom / Other")
    
    choice = input("\nEnter choice (1-8): ").strip()
    
    providers = {
        "1": ("openai", "OpenAI", "https://platform.openai.com/account/api-keys"),
        "2": ("anthropic", "Anthropic", "https://console.anthropic.com/"),
        "3": ("gemini", "Google Gemini", "https://aistudio.google.com/app/apikey"),
        "4": ("kimi", "Moonshot Kimi", "https://platform.moonshot.cn/"),
        "5": ("qwen", "Qwen", "https://dashscope.console.aliyun.com/"),
        "6": ("deepseek", "DeepSeek", "https://platform.deepseek.com/"),
        "7": ("ollama", "Ollama", "https://ollama.ai/"),
        "8": ("custom", "Custom", "your API endpoint"),
    }
    
    provider, provider_name, api_url = providers.get(choice, ("openai", "OpenAI", ""))
    
    print(f"\n[{provider_name}]")
    print(f"To get your API key, visit: {api_url}")
    
    if provider == "ollama":
        print("\nFor Ollama, make sure it's running locally.")
        print("Default endpoint: http://localhost:11434/v1/chat/completions")
        api_key = ""
        endpoint = input("Endpoint (press Enter for default): ").strip() or "http://localhost:11434/v1/chat/completions"
        model = input("Model name (e.g., llama3, mistral): ").strip() or "llama3"
    elif provider == "custom":
        api_key = input("API Key (or press Enter for none): ").strip()
        endpoint = input("API Endpoint: ").strip()
        model = input("Model name: ").strip()
    else:
        api_key = input(f"\nEnter your {provider_name} API Key: ").strip()
        endpoint = ""
        model = input(f"Model (press Enter for default): ").strip()
        
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "gemini": "gemini-1.5-flash",
            "kimi": "kimi-k2",
            "qwen": "qwen-turbo",
            "deepseek": "deepseek-chat",
        }
        model = model or defaults.get(provider, "gpt-4")
    
    write_config(provider, model, api_key, endpoint)
    
    print("\n" + "=" * 50)
    print("[Setup Complete]")
    print("=" * 50)
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print("\nYou can now use:")
    print("  ask /ask 'your prompt'")
    print("  ask /estimate 'your prompt'")
    print("  ask /budget")
    print("=" * 50)


def write_config(provider, model, api_key, endpoint):
    """Write config file."""
    config_content = f"""llm_provider: {provider}
model: {model}
api_key: {api_key}
endpoint: "{endpoint}"

budget:
  daily_limit: 100000
  monthly_limit: 3000000
  warn_threshold: 0.8
  block_excess: false

pricing:
  input_per_1k: 0.01
  output_per_1k: 0.03

optimization:
  minify_prompts: true
  trim_context: true
  enable_cache: true

clarifying_questions:
  enabled: true

cache_dir: .smartllm_cache
"""
    
    config_path = os.path.join(os.getcwd(), "smartllm.yaml")
    with open(config_path, "w") as f:
        f.write(config_content)


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="Run first-time setup")
    parser.add_argument("command", nargs="?", help="Command to run")
    args, unknown = parser.parse_known_args()
    
    if args.setup:
        first_time_setup()
    else:
        from nantoken.slash_cli import main as cli_main
        sys.argv = [sys.argv[0]] + unknown if unknown else [sys.argv[0]]
        cli_main()


if __name__ == "__main__":
    main()