#!/usr/bin/env python3
"""NanToken Interactive Shell - Slash command interface"""

import os
import sys
import json
from pathlib import Path

from nantoken.config import load_config, create_default_config, Config, save_config
from nantoken.core import SmartLLM, print_analysis_report
from nantoken.integrator import CodeIntegrator


class SmartLLMShell:
    """Interactive shell with slash commands."""
    
    COMMANDS = {
        "/help": "Show all commands",
        "/analyze": "Analyze a prompt (usage: /analyze <prompt>)",
        "/optimize": "Optimize a prompt (usage: /optimize <prompt>)",
        "/run": "Run prompt through LLM (usage: /run <prompt>)",
        "/budget": "Show budget status",
        "/budget set daily <num>": "Set daily limit",
        "/budget set monthly <num>": "Set monthly limit",
        "/cache": "Show cache stats",
        "/cache clear": "Clear all cache",
        "/project": "Analyze project files",
        "/project analyze <filename>": "Analyze specific file",
        "/config": "Show current config",
        "/config set <key> <value>": "Update config",
        "/create": "Create code file (usage: /create <prompt> -o <file>)",
        "/quit": "Exit SmartLLM",
    }
    
    def __init__(self):
        self.config_path = "smartllm.yaml"
        self.config = self._load_or_init()
        self.smartllm = SmartLLM(self.config)
        from nantoken.runner import nantokenRunner
        self.runner = SmartLLMRunner(self.config, self.config_path)
        self.running = True
    
    def _load_or_init(self) -> Config:
        """Load config or create default."""
        if os.path.exists(self.config_path):
            return load_config(self.config_path)
        return Config()
    
    def first_time_setup(self) -> bool:
        """Run first-time setup wizard."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                content = f.read()
                if "YOUR_API_KEY_HERE" not in content:
                    return False
        
        print("\n" + "=" * 50)
        print("[Welcome to SmartLLM - First Time Setup]")
        print("=" * 50)
        
        print("\nLet's configure your SmartLLM installation.\n")
        
        provider = input("LLM Provider (openai/anthropic/gemini) [openai]: ").strip() or "openai"
        model = input("Model name [gpt-4]: ").strip() or "gpt-4"
        api_key = input("API Key: ").strip()
        
        print("\n--- Budget Settings ---")
        daily = input("Daily token limit [100000]: ").strip() or "100000"
        monthly = input("Monthly token limit [3000000]: ").strip() or "3000000"
        
        print("\n--- Pricing (per 1K tokens) ---")
        input_price = input("Input price ($) [0.01]: ").strip() or "0.01"
        output_price = input("Output price ($) [0.03]: ").strip() or "0.03"
        
        config = Config(
            llm_provider=provider,
            model=model,
            api_key=api_key,
            budget=type('obj', (), {
                'daily_limit': int(daily),
                'monthly_limit': int(monthly),
                'warn_threshold': 0.8,
                'block_excess': False
            })(),
            pricing=type('obj', (), {
                'input_per_1k': float(input_price),
                'output_per_1k': float(output_price)
            })(),
            optimization=type('obj', (), {
                'minify_prompts': True,
                'trim_context': True,
                'enable_cache': True,
                'cache_ttl_hours': 24
            })(),
            clarifying_questions=type('obj', (), {
                'enabled': True,
                'always_ask': False,
                'threshold_tokens': 500
            })(),
            cache_dir=".smartllm_cache",
            log_level="INFO"
        )
        
        save_config(config, self.config_path)
        
        print("\n✅ Setup complete! Config saved to smartllm.yaml")
        print("You can edit this file anytime to change settings.\n")
        
        self.config = config
        self.smartllm = SmartLLM(config)
        return True
    
    def print_help(self):
        """Print help message."""
        print("\n" + "=" * 50)
        print("[Help] SmartLLM Commands")
        print("=" * 50)
        for cmd, desc in self.COMMANDS.items():
            print(f"  {cmd:<30} {desc}")
        print("=" * 50)
    
    def run(self):
        """Run the interactive shell."""
        self.first_time_setup()
        
        print("\n" + "=" * 50)
        print("[Interactive] SmartLLM Interactive Shell")
        print("=" * 50)
        print("Type /help for commands or /quit to exit")
        print("=" * 50 + "\n")
        
        while self.running:
            try:
                prompt = input("smartllm> ").strip()
                if not prompt:
                    continue
                
                self.handle_command(prompt)
            except KeyboardInterrupt:
                print("\nUse /quit to exit")
            except EOFError:
                break
        
        print("\n[Goodbye]")
    
    def handle_command(self, prompt: str):
        """Handle a command."""
        parts = prompt.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "/quit" or cmd == "/exit":
            self.running = False
        
        elif cmd == "/help":
            self.print_help()
        
        elif cmd == "/analyze":
            user_prompt = " ".join(args)
            if not user_prompt:
                print("Usage: /analyze <prompt>")
                return
            
            analysis = self.smartllm.analyze(user_prompt)
            print_analysis_report(analysis)
            
            if analysis["questions"]:
                print("\n⚠️ Clarifying questions detected. Answer with:")
                print("  /answer <question_id> <answer>")
        
        elif cmd == "/optimize":
            user_prompt = " ".join(args)
            if not user_prompt:
                print("Usage: /optimize <prompt>")
                return
            
            self.smartllm.analyze(user_prompt)
            result = self.smartllm.optimize(user_prompt)
            
            print("\n[Optimization] Optimization Result:")
            print(f"  Original: {result['original_estimate'].get('input_tokens', 'N/A')} tokens")
            print(f"  Optimized: {result['optimized_estimate']['input_tokens']} tokens")
            print(f"  Savings: {result['savings'].get('estimated_token_reduction', 0)} tokens")
            print(f"  Cost reduction: ${result['cost_reduction']:.4f}")
            
            if args and "-s" in args:
                print(f"\nOptimized prompt:\n{result['optimized_prompt']}")
        
        elif cmd == "/run":
            user_prompt = " ".join(args)
            if not user_prompt:
                print("Usage: /run <prompt>")
                return
            
            self.runner.run(user_prompt)
            print(f"\n{self.runner.session_summary()}")
        
        elif cmd == "/budget":
            if args and args[0] == "set":
                if len(args) >= 3:
                    key = args[1]
                    value = args[2]
                    if key == "daily":
                        self.config.budget.daily_limit = int(value)
                    elif key == "monthly":
                        self.config.budget.monthly_limit = int(value)
                    save_config(self.config, self.config_path)
                    print(f"✅ Updated {key} limit to {value}")
                else:
                    print("Usage: /budget set daily|monthly <value>")
            else:
                print(self.smartllm.get_budget_report())
        
        elif cmd == "/cache":
            if args and args[0] == "clear":
                self.smartllm.optimizer.clear_cache()
                print("✅ Cache cleared")
            else:
                stats = self.smartllm.get_cache_report()
                print(f"\n[Cache] {stats.get('total_entries', 0)} entries, {stats.get('valid_entries', 0)} valid")
        
        elif cmd == "/project":
            if len(args) >= 2 and args[0] == "analyze":
                analysis = self.smartllm.integrator.analyze_file(args[1])
                print(f"\n[File] {analysis.path}")
                print(f"   Language: {analysis.language}, Lines: {analysis.lines}")
            else:
                stats = self.smartllm.get_project_stats()
                print(f"\n[Project] {stats['total_files']} files, {stats['total_lines']} lines")
        
        elif cmd == "/config":
            if len(args) >= 2 and args[0] == "set":
                key = args[1]
                value = args[2] if len(args) > 2 else ""
                
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    save_config(self.config, self.config_path)
                    print(f"✅ Updated {key} = {value}")
                else:
                    print(f"Unknown config: {key}")
            else:
                print(f"\n⚙️ Current Config:")
                print(f"  Provider: {self.config.llm_provider}")
                print(f"  Model: {self.config.model}")
                print(f"  Daily budget: {self.config.budget.daily_limit}")
                print(f"  Monthly budget: {self.config.budget.monthly_limit}")
        
        elif cmd == "/create":
            user_prompt = ""
            output_file = None
            
            for i, arg in enumerate(args):
                if arg == "-o" and i + 1 < len(args):
                    output_file = args[i + 1]
                else:
                    user_prompt += arg + " "
            
            if not user_prompt:
                print("Usage: /create <prompt> -o <file>")
                return
            
            suggested = self.smartllm.integrator.suggest_file_name(user_prompt)
            file_path = output_file or suggested or "output.py"
            
            content = f'''# Generated by SmartLLM
# Prompt: {user_prompt[:100]}

# TODO: Implement your code here

def main():
    pass

if __name__ == "__main__":
    main()
'''
            
            success, msg = self.smartllm.create_code_file(file_path, content)
            print(f"{'✅' if success else '❌'} {msg}")
        
        elif cmd == "/answer":
            print("💡 Tip: Use /analyze first, then answer questions when prompted")
        
        else:
            print(f"Unknown command: {cmd}")
            print("Type /help for available commands")


def main():
    shell = SmartLLMShell()
    shell.run()


if __name__ == "__main__":
    main()
