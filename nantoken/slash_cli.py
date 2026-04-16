#!/usr/bin/env python3
"""
NanToken Slash CLI - Simple slash commands for quick LLM usage

Usage:
    /ask "prompt"          - Send prompt to LLM with tracking
    /estimate "prompt"     - Estimate tokens and cost only
    /plan "task"           - Plan a complex task
    /budget                - Show budget status
    
    [prompt]               - Inline style (in scripts)
    
Examples:
    nantoken /ask write a hello world in python
    nantoken /estimate create a website
    nantoken /plan build a rest api with auth
    nantoken [write hello world]
"""

import os
import sys
import re
import argparse
from typing import Optional

from nantoken.config import load_config, Config
from nantoken.estimator import TokenEstimator
from nantoken.budget import BudgetManager
from nantoken.universal_client import UniversalLLMClient, format_usage_line
from nantoken.task_planner import TaskPlanner, format_task_plan, format_task_ask


def parse_args():
    """Parse arguments with support for slash commands."""
    if len(sys.argv) < 2:
        return None, None
    
    first_arg = sys.argv[1]
    
    if first_arg.startswith("/"):
        command = first_arg[1:].lower()
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        return command, prompt
    
    if first_arg.startswith("[") and first_arg.endswith("]"):
        prompt = first_arg[1:-1]
        return "inline", prompt
    
    if first_arg.startswith("[") and "]" in first_arg:
        match = re.match(r'\[(.+?)\](.*)', " ".join(sys.argv[1:]))
        if match:
            prompt = match.group(1)
            return "inline", prompt
    
    return None, first_arg


def load_full_config() -> Config:
    """Load config with extended model pricing."""
    config = load_config()
    
    extended_pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "kimi": {"input": 0.01, "output": 0.03},
        "kimi-k2": {"input": 0.01, "output": 0.03},
        "qwen-turbo": {"input": 0.002, "output": 0.006},
        "qwen-plus": {"input": 0.004, "output": 0.012},
        "qwen-max": {"input": 0.02, "output": 0.06},
        "deepseek-chat": {"input": 0.00014, "output": 0.00028},
        "deepseek-coder": {"input": 0.00014, "output": 0.00028},
        "llama-3-70b": {"input": 0.0007, "output": 0.0008},
        "llama-3-8b": {"input": 0.0002, "output": 0.0002},
        "mistral-large": {"input": 0.002, "output": 0.006},
    }
    
    config.pricing.model_pricing = extended_pricing
    return config


def run_ask(prompt: str, config: Config):
    """Run prompt through LLM."""
    if not prompt:
        print("[Error] No prompt provided")
        return
    
    print(f"\n[Ask] {config.llm_provider}/{config.model}")
    print(f"Prompt: {prompt[:60]}...")
    print("-" * 40)
    
    llm = UniversalLLMClient(
        provider=config.llm_provider,
        model=config.model,
        api_key=config.api_key,
        pricing=config.pricing.model_pricing,
    )
    
    estimator = TokenEstimator(model=config.model)
    
    estimate = estimator.estimate_request(prompt, "", 500)
    est_cost = estimator.estimate_cost(
        estimate["input_tokens"],
        estimate["expected_output_tokens"],
        config.pricing.input_per_1k,
        config.pricing.output_per_1k,
    )
    
    print(f"[Est] Input: {estimate['input_tokens']} | Output: ~{estimate['expected_output_tokens']} | Cost: ~${est_cost:.4f}")
    print()
    
    try:
        response, usage = llm.call(prompt)
        
        print(response)
        print()
        print(format_usage_line(usage))
        
        budget = BudgetManager(
            daily_limit=config.budget.daily_limit,
            monthly_limit=config.budget.monthly_limit,
        )
        budget.add_usage(usage["input_tokens"], usage["output_tokens"], usage["cost"], prompt, response)
        
    except Exception as e:
        print(f"[Error] {str(e)}")


def run_estimate(prompt: str, config: Config):
    """Estimate tokens and cost only."""
    if not prompt:
        print("[Error] No prompt provided")
        return
    
    estimator = TokenEstimator(model=config.model)
    
    estimate = estimator.estimate_request(prompt, "", 500)
    cost = estimator.estimate_cost(
        estimate["input_tokens"],
        estimate["expected_output_tokens"],
        config.pricing.input_per_1k,
        config.pricing.output_per_1k,
    )
    
    budget = BudgetManager(
        daily_limit=config.budget.daily_limit,
        monthly_limit=config.budget.monthly_limit,
    )
    status = budget.get_status()
    
    print()
    print("=" * 50)
    print(f"[Estimate] {config.llm_provider}/{config.model}")
    print("=" * 50)
    print(f"Prompt: {prompt[:50]}...")
    print(f"Input:   {estimate['input_tokens']} tokens")
    print(f"Output:  ~{estimate['expected_output_tokens']} tokens")
    print(f"Total:   ~{estimate['total_tokens']} tokens")
    print(f"Cost:    ~${cost:.4f}")
    print()
    print(f"Daily budget: {status.daily_used:,}/{status.daily_limit:,} ({status.daily_percent:.1f}%)")
    print(f"Remaining:    {status.daily_remaining:,} tokens")
    print("=" * 50)


def run_plan(prompt: str, config: Config):
    """Plan a complex task."""
    if not prompt:
        print("[Error] No task description provided")
        return
    
    planner = TaskPlanner()
    
    plan = planner.plan_task(prompt, config.model, config.llm_provider)
    
    print(format_task_plan(plan))
    
    confirm = input(format_task_ask(plan)).strip().lower()
    
    if confirm not in ["", "y", "yes"]:
        print("[Cancelled]")
        return
    
    print("\n[Executing...]")
    run_ask(prompt, config)


def run_budget(config: Config):
    """Show budget status."""
    budget = BudgetManager(
        daily_limit=config.budget.daily_limit,
        monthly_limit=config.budget.monthly_limit,
    )
    status = budget.get_status()
    
    print()
    print("=" * 40)
    print("[Budget Status]")
    print("=" * 40)
    print(f"Daily:   {status.daily_used:,} / {status.daily_limit:,} ({status.daily_percent:.1f}%)")
    print(f"Monthly: {status.monthly_used:,} / {status.monthly_limit:,} ({status.monthly_percent:.1f}%)")
    print(f"Remaining today: {status.daily_remaining:,} tokens")
    print("=" * 40)


def run_inline(prompt: str, config: Config):
    """Run inline style prompt [prompt]."""
    run_ask(prompt, config)


def main():
    """Main entry point."""
    if len(sys.argv) == 1:
        print("NanToken Slash CLI")
        print()
        print("Usage:")
        print("  /ask <prompt>        - Send prompt to LLM")
        print("  /estimate <prompt>  - Estimate tokens and cost")
        print("  /plan <task>         - Plan complex task")
        print("  /budget              - Show budget status")
        print("  [prompt]             - Inline style")
        print()
        print("Examples:")
        print('  nantoken /ask "write hello world in python"')
        print('  nantoken [create a simple website]')
        print('  nantoken /budget')
        return
    
    command, prompt = parse_args()
    
    if command is None and prompt is None:
        print("[Error] Unknown command. Use --help for usage.")
        return
    
    config = load_full_config()
    
    if command == "ask" or command == "run":
        run_ask(prompt, config)
    elif command == "estimate":
        run_estimate(prompt, config)
    elif command == "plan":
        run_plan(prompt, config)
    elif command == "budget":
        run_budget(config)
    elif command == "inline":
        run_inline(prompt, config)
    else:
        run_ask(f"{command} {prompt}".strip(), config)


if __name__ == "__main__":
    main()
