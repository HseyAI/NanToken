"""
SmartLLM Integration Module - Use with Claude Code, OpenCode, or any LLM wrapper

Usage:
    from nantoken.integrate import smart_ask, smart_estimate, smart_track
    
    # Ask with auto-tracking
    response = smart_ask("write a function")
    
    # Estimate without calling LLM
    est = smart_estimate("create a website")
    
    # Track usage from any LLM call
    track_usage(input_tokens=100, output_tokens=500, model="gpt-4")
"""

from typing import Dict, Optional, Tuple
from nantoken.config import load_config, Config
from nantoken.estimator import TokenEstimator
from nantoken.budget import BudgetManager
from nantoken.universal_client import UniversalLLMClient, format_usage_line
from nantoken.task_planner import TaskPlanner, format_task_plan


def get_config() -> Config:
    """Load SmartLLM config with extended pricing."""
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


def smart_ask(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    show_estimate: bool = True,
) -> Tuple[str, Dict]:
    """
    Send prompt to LLM with automatic tracking.
    
    Returns: (response, usage_info)
    """
    config = get_config()
    
    if model:
        config.model = model
    if provider:
        config.llm_provider = provider
    
    if show_estimate:
        estimator = TokenEstimator(model=config.model)
        estimate = estimator.estimate_request(prompt, system_prompt, 500)
        est_cost = estimator.estimate_cost(
            estimate["input_tokens"],
            estimate["expected_output_tokens"],
            config.pricing.input_per_1k,
            config.pricing.output_per_1k,
        )
        print(f"\n[SmartLLM Est] {config.model} | {estimate['input_tokens']} in | ~{estimate['expected_output_tokens']} out | ~${est_cost:.4f}")
    
    llm = UniversalLLMClient(
        provider=config.llm_provider,
        model=config.model,
        api_key=config.api_key,
        pricing=config.pricing.model_pricing,
    )
    
    response, usage = llm.call(prompt, system_prompt)
    
    print(format_usage_line(usage))
    
    budget = BudgetManager(
        daily_limit=config.budget.daily_limit,
        monthly_limit=config.budget.monthly_limit,
    )
    budget.add_usage(usage["input_tokens"], usage["output_tokens"], usage["cost"], prompt, response)
    
    return response, usage


def smart_estimate(prompt: str, model: Optional[str] = None) -> Dict:
    """
    Estimate tokens and cost without calling LLM.
    
    Returns: dict with estimate details
    """
    config = get_config()
    
    if model:
        config.model = model
    
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
    
    return {
        "model": config.model,
        "provider": config.llm_provider,
        "input_tokens": estimate["input_tokens"],
        "output_tokens": estimate["expected_output_tokens"],
        "total_tokens": estimate["total_tokens"],
        "estimated_cost": cost,
        "budget_remaining": status.daily_remaining,
        "budget_percent": status.daily_percent,
    }


def smart_track(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4",
    provider: str = "openai",
    prompt: str = "",
    response: str = "",
) -> Dict:
    """
    Track usage from any LLM call.
    
    Use this to track calls made through other wrappers (Claude Code, etc.)
    """
    config = get_config()
    
    llm = UniversalLLMClient(
        provider=provider,
        model=model,
        pricing=config.pricing.model_pricing,
    )
    
    cost = llm.calculate_cost(input_tokens, output_tokens)
    
    budget = BudgetManager(
        daily_limit=config.budget.daily_limit,
        monthly_limit=config.budget.monthly_limit,
    )
    budget.add_usage(input_tokens, output_tokens, cost, prompt, response)
    
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost": cost,
    }


def smart_plan(task: str) -> Dict:
    """Plan a complex task with token forecast."""
    config = get_config()
    
    planner = TaskPlanner()
    plan = planner.plan_task(task, config.model, config.llm_provider)
    
    return {
        "task": task,
        "model": config.model,
        "provider": config.llm_provider,
        "complexity": plan.complexity,
        "total_estimated_tokens": plan.total_estimated_tokens,
        "estimated_cost": plan.estimated_cost,
        "steps": [
            {"step": s.step_number, "description": s.description, "tokens": s.estimated_input_tokens + s.estimated_output_tokens}
            for s in plan.steps
        ],
    }


def format_estimate(estimate: Dict) -> str:
    """Format estimate as one line."""
    return (
        f"[Est] {estimate['model']} | "
        f"In: {estimate['input_tokens']} | "
        f"Out: ~{estimate['output_tokens']} | "
        f"Total: {estimate['total_tokens']} | "
        f"Cost: ${estimate['estimated_cost']:.4f}"
    )


def format_track(usage: Dict) -> str:
    """Format tracking result as one line."""
    return (
        f"[Track] {usage['total_tokens']} tokens | ${usage['cost']:.4f}"
    )


__all__ = [
    "smart_ask",
    "smart_estimate", 
    "smart_track",
    "smart_plan",
    "format_estimate",
    "format_track",
    "get_config",
]
