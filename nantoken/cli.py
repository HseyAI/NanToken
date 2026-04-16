#!/usr/bin/env python3
"""NanToken CLI - Intelligent LLM Token Tracker"""

import os
import sys
import argparse
import json
from pathlib import Path

from nantoken.config import load_config, create_default_config, Config
from nantoken.core import SmartLLM, print_analysis_report
from nantoken.integrator import CodeIntegrator


def cmd_init(args):
    """Initialize a new SmartLLM project."""
    config_path = args.config or "smartllm.yaml"
    
    if os.path.exists(config_path):
        print(f"Config already exists: {config_path}")
        return
    
    create_default_config(config_path)
    print(f"[OK] Created default config: {config_path}")
    print("\nEdit the config file to add your API key and preferences.")


def cmd_analyze(args):
    """Analyze a prompt before sending to LLM."""
    config = load_config(args.config)
    smartllm = SmartLLM(config)
    
    prompt = args.prompt
    if args.file and os.path.exists(args.file):
        with open(args.file, "r") as f:
            prompt = f.read()
    
    system_prompt = args.system or ""
    
    analysis = smartllm.analyze(prompt, system_prompt)
    print_analysis_report(analysis)
    
    if analysis["questions"]:
        print("\n[!] Please answer clarifying questions to proceed:")
        for q in analysis["questions"]:
            print(f"  - {q['question']}")


def cmd_optimize(args):
    """Optimize a prompt."""
    config = load_config(args.config)
    smartllm = SmartLLM(config)
    
    prompt = args.prompt
    if args.file and os.path.exists(args.file):
        with open(args.file, "r") as f:
            prompt = f.read()
    
    system_prompt = args.system or ""
    
    optimization = smartllm.optimize(prompt, system_prompt)
    
    print("\n" + "=" * 50)
    print("[Optimization] OPTIMIZATION REPORT")
    print("=" * 50)
    print(f"\nOriginal length: {len(prompt)} chars")
    print(f"Optimized length: {len(optimization['optimized_prompt'])} chars")
    print(f"Reduction: {optimization['savings']['reduction_percent']:.1f}%")
    print(f"\nOriginal tokens (est): {optimization['original_estimate'].get('input_tokens', 'N/A')}")
    print(f"Optimized tokens (est): {optimization['optimized_estimate']['input_tokens']}")
    print(f"Token savings: {optimization['savings'].get('estimated_token_reduction', 0)}")
    print(f"Cost reduction: ${optimization['cost_reduction']:.4f}")
    
    if args.show_prompt:
        print("\n[Prompt] Optimized Prompt:")
        print("-" * 40)
        print(optimization["optimized_prompt"])
        print("-" * 40)
    
    print("=" * 50)


def cmd_budget(args):
    """Show budget status and usage."""
    config = load_config(args.config)
    smartllm = SmartLLM(config)
    
    status = smartllm.budget.get_status()
    print(smartllm.get_budget_report())
    
    if args.stats:
        stats = smartllm.budget.get_usage_stats(args.stats)
        print(f"\n[Stats] Usage Stats (last {args.stats} days):")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Total tokens: {stats['total_tokens']:,}")
        print(f"   Total cost: ${stats['total_cost']:.2f}")
        print(f"   Avg tokens/request: {stats['avg_tokens_per_request']:.0f}")


def cmd_cache(args):
    """Manage cache."""
    config = load_config(args.config)
    smartllm = SmartLLM(config)
    
    if args.clear:
        smartllm.optimizer.clear_cache()
        print("✅ Cache cleared")
    elif args.clear_expired:
        smartllm.optimizer.clear_expired()
        print("✅ Expired cache entries cleared")
    else:
        stats = smartllm.get_cache_report()
        print("\n[Cache] Cache Status:")
        print(f"   Enabled: {stats['enabled']}")
        print(f"   Total entries: {stats.get('total_entries', 0)}")
        print(f"   Valid entries: {stats.get('valid_entries', 0)}")
        print(f"   Expired entries: {stats.get('expired_entries', 0)}")
        print(f"   Cache dir: {stats.get('cache_dir', 'N/A')}")


def cmd_project(args):
    """Show project stats and analyze files."""
    integrator = CodeIntegrator(args.root or ".")
    
    if args.analyze:
        analysis = integrator.analyze_file(args.analyze)
        print(f"\n[File] {analysis.path}")
        print(f"   Language: {analysis.language}")
        print(f"   Lines: {analysis.lines:,}")
        print(f"   Est. tokens: {analysis.tokens_estimate:,}")
        print(f"   Functions: {len(analysis.functions)}")
        print(f"   Imports: {len(analysis.imports)}")
    else:
        stats = integrator.get_project_stats()
        print("\n[Project] Project Stats:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total lines: {stats['total_lines']:,}")
        print(f"   Est. tokens: {stats['total_tokens_estimate']:,}")
        
        print("\n[Breakdown] By Language:")
        for lang, data in sorted(stats["by_language"].items()):
            print(f"   {lang}: {data['files']} files, {data['lines']} lines")


def cmd_create(args):
    """Create a code file from prompt."""
    config = load_config(args.config)
    smartllm = SmartLLM(config)
    
    prompt = args.prompt or ""
    
    if args.prompt_file and os.path.exists(args.prompt_file):
        with open(args.prompt_file, "r") as f:
            prompt = f.read()
    
    integrator = CodeIntegrator(args.root or ".")
    suggested_name = integrator.suggest_file_name(prompt)
    
    file_path = args.output or suggested_name or "output.py"
    
    content = f'''# Generated by SmartLLM
# Prompt: {prompt[:100]}...

# TODO: Add your implementation here

def main():
    pass

if __name__ == "__main__":
    main()
'''
    
    success, msg = smartllm.create_code_file(file_path, content, args.overwrite)
    print(f"[OK]" if success else "[X] {msg}")


def cmd_run(args):
    """Run prompt through LLM with optimization and tracking."""
    from nantoken.runner import nantokenRunner
    
    config = load_config(args.config)
    runner = SmartLLMRunner(config, args.config)
    
    if args.interactive:
        runner.interactive_mode()
    else:
        prompt = args.prompt
        if args.file:
            with open(args.file, "r") as f:
                prompt = f.read()
        
        if not prompt:
            print("Error: No prompt provided")
            return
        
        if args.plan:
            runner.run_with_plan(prompt, auto_confirm=args.auto)
        else:
            runner.run(prompt, args.system or "", use_tui=args.tui)
        
        print(f"\n{runner.session_summary()}")


def main():
    parser = argparse.ArgumentParser(
        description="SmartLLM - Intelligent LLM Request Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Path to config file (default: smartllm.yaml)",
        default=None,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    p_init = subparsers.add_parser("init", help="Initialize SmartLLM config")
    p_init.set_defaults(func=cmd_init)
    p_init.add_argument("config", nargs="?", default="smartllm.yaml", help="Config file path")
    
    p_analyze = subparsers.add_parser("analyze", help="Analyze a prompt")
    p_analyze.set_defaults(func=cmd_analyze)
    p_analyze.add_argument("prompt", nargs="?", help="Prompt text")
    p_analyze.add_argument("-f", "--file", help="Read prompt from file")
    p_analyze.add_argument("-s", "--system", help="System prompt")
    
    p_opt = subparsers.add_parser("optimize", help="Optimize a prompt")
    p_opt.set_defaults(func=cmd_optimize)
    p_opt.add_argument("prompt", nargs="?", help="Prompt text")
    p_opt.add_argument("-f", "--file", help="Read prompt from file")
    p_opt.add_argument("-s", "--system", help="System prompt")
    p_opt.add_argument("--show-prompt", action="store_true", help="Show optimized prompt")
    
    p_budget = subparsers.add_parser("budget", help="Show budget status")
    p_budget.set_defaults(func=cmd_budget)
    p_budget.add_argument("--stats", type=int, help="Show stats for last N days")
    
    p_cache = subparsers.add_parser("cache", help="Manage cache")
    p_cache.set_defaults(func=cmd_cache)
    p_cache.add_argument("--clear", action="store_true", help="Clear all cache")
    p_cache.add_argument("--clear-expired", action="store_true", help="Clear expired entries")
    
    p_run = subparsers.add_parser("run", help="Run prompt through LLM")
    p_run.set_defaults(func=cmd_run)
    p_run.add_argument("prompt", nargs="?", help="Prompt text")
    p_run.add_argument("-f", "--file", help="Read prompt from file")
    p_run.add_argument("-s", "--system", help="System prompt")
    p_run.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    p_run.add_argument("--tui", action="store_true", help="Use TUI mode")
    p_run.add_argument("--plan", action="store_true", help="Plan task before running")
    p_run.add_argument("--auto", action="store_true", help="Auto-confirm plan")
    
    p_proj = subparsers.add_parser("project", help="Project file analysis")
    p_proj.set_defaults(func=cmd_project)
    p_proj.add_argument("-r", "--root", help="Project root directory")
    p_proj.add_argument("-a", "--analyze", help="Analyze specific file")
    
    p_create = subparsers.add_parser("create", help="Create a code file")
    p_create.set_defaults(func=cmd_create)
    p_create.add_argument("prompt", nargs="?", help="Prompt describing what to create")
    p_create.add_argument("-f", "--prompt-file", help="Read prompt from file")
    p_create.add_argument("-o", "--output", help="Output file path")
    p_create.add_argument("-r", "--root", help="Project root")
    p_create.add_argument("--overwrite", action="store_true", help="Overwrite existing file")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
