"""NanToken MCP Server - Token tracking tools for AI coding terminals.

Exposes token estimation, budget tracking, usage analytics, and task planning
as MCP tools that work inside Claude Code, Cursor, Windsurf, and any
MCP-compatible editor.

Usage:
    python -m nantoken              # Start MCP server (stdio)
    mcp run nantoken/mcp_server.py  # Test with MCP CLI
"""

import os
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

from nantoken.config import load_config, Config
from nantoken.core import SmartLLM
from nantoken.estimator import TokenEstimator
from nantoken.task_planner import TaskPlanner, format_task_plan

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("NanToken", instructions=(
    "NanToken provides token tracking and budget management for LLM usage. "
    "Use these tools to estimate costs before sending prompts, track token "
    "usage, monitor budgets, and plan complex tasks with cost forecasts."
))

# ---------------------------------------------------------------------------
# Lazy singleton & session state
# ---------------------------------------------------------------------------
_smartllm: Optional[SmartLLM] = None

_session = {
    "started_at": datetime.now().isoformat(),
    "total_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost": 0.0,
}


def _get_smartllm() -> SmartLLM:
    """Return a shared SmartLLM instance, creating it on first use."""
    global _smartllm
    if _smartllm is None:
        config_path = os.environ.get("NANTOKEN_CONFIG")
        _smartllm = SmartLLM(config_path=config_path)
    return _smartllm


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def token_estimate(
    prompt: str,
    model: str = "",
    expected_output_tokens: int = 500,
) -> str:
    """Estimate tokens and cost for a prompt before sending it to an LLM.

    Args:
        prompt: The prompt text to estimate.
        model: Optional model name override (default: from config).
        expected_output_tokens: Expected response length in tokens (default: 500).
    """
    try:
        slm = _get_smartllm()

        # Optionally override model for this estimate
        estimator = slm.estimator
        if model:
            estimator = TokenEstimator(model=model)

        estimate = estimator.estimate_request(
            user_prompt=prompt,
            system_prompt="",
            expected_output_tokens=expected_output_tokens,
        )

        config = slm.config
        # Use model-specific pricing if available
        pricing = config.pricing
        model_name = model or config.model
        if model_name in pricing.model_pricing:
            mp = pricing.model_pricing[model_name]
            input_price = mp["input"]
            output_price = mp["output"]
        else:
            input_price = pricing.input_per_1k
            output_price = pricing.output_per_1k

        cost = estimator.estimate_cost(
            input_tokens=estimate["input_tokens"],
            output_tokens=estimate["expected_output_tokens"],
            input_price_per_1k=input_price,
            output_price_per_1k=output_price,
        )

        # Budget check
        can_proceed, budget_msg = slm.budget.check_request(estimate["total_tokens"])

        lines = [
            f"[Estimate] {model_name}",
            "=" * 50,
            f"Input tokens:    {estimate['input_tokens']:,}",
            f"Output tokens:   ~{estimate['expected_output_tokens']:,}",
            f"Total tokens:    ~{estimate['total_tokens']:,}",
            f"Estimated cost:  ${cost:.4f}",
            "",
            f"Budget: {budget_msg}",
            "=" * 50,
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error estimating tokens: {e}"


@mcp.tool()
def token_track(
    input_tokens: int,
    output_tokens: int,
    model: str = "",
    prompt: str = "",
) -> str:
    """Record token usage from an LLM call for budget tracking.

    Call this after an LLM interaction to log the tokens used.

    Args:
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens used.
        model: Optional model name (for cost calculation).
        prompt: Optional prompt text (for logging).
    """
    try:
        slm = _get_smartllm()

        config = slm.config
        model_name = model or config.model
        pricing = config.pricing

        if model_name in pricing.model_pricing:
            mp = pricing.model_pricing[model_name]
            input_price = mp["input"]
            output_price = mp["output"]
        else:
            input_price = pricing.input_per_1k
            output_price = pricing.output_per_1k

        cost = slm.estimator.estimate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_price_per_1k=input_price,
            output_price_per_1k=output_price,
        )

        slm.budget.add_usage(input_tokens, output_tokens, cost, prompt or "(tracked)")

        # Update session
        _session["total_calls"] += 1
        _session["total_input_tokens"] += input_tokens
        _session["total_output_tokens"] += output_tokens
        _session["total_cost"] += cost

        total = input_tokens + output_tokens
        status = slm.budget.get_status()

        lines = [
            f"[Tracked] {model_name}",
            f"Tokens: {input_tokens:,} in + {output_tokens:,} out = {total:,} total",
            f"Cost: ${cost:.4f}",
            "",
            f"Session total: {_session['total_calls']} calls, "
            f"{_session['total_input_tokens'] + _session['total_output_tokens']:,} tokens, "
            f"${_session['total_cost']:.4f}",
            f"Daily budget: {status.daily_used:,}/{status.daily_limit:,} "
            f"({status.daily_percent:.1f}%)",
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error tracking tokens: {e}"


@mcp.tool()
def token_budget() -> str:
    """Show current token budget status including daily and monthly usage."""
    try:
        slm = _get_smartllm()
        return slm.get_budget_report()
    except Exception as e:
        return f"Error getting budget: {e}"


@mcp.tool()
def token_stats(days: int = 7) -> str:
    """Show token usage analytics for the past N days.

    Args:
        days: Number of days to look back (default: 7).
    """
    try:
        slm = _get_smartllm()
        stats = slm.budget.get_usage_stats(days=days)

        if stats["total_requests"] == 0:
            return f"No usage recorded in the past {days} days."

        lines = [
            f"[Usage Stats] Last {days} days",
            "=" * 40,
            f"Total requests:    {stats['total_requests']:,}",
            f"Total tokens:      {stats['total_tokens']:,}",
            f"Total cost:        ${stats['total_cost']:.4f}",
            f"Avg tokens/req:    {stats['avg_tokens_per_request']:,.0f}",
            f"Avg cost/req:      ${stats['avg_cost_per_request']:.4f}",
            "=" * 40,
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting stats: {e}"


@mcp.tool()
def token_plan(task: str, model: str = "") -> str:
    """Plan a complex task with per-step token forecasts and cost estimates.

    Breaks a task into steps and estimates the tokens and cost for each step.

    Args:
        task: Description of the task to plan.
        model: Optional model name override.
    """
    try:
        slm = _get_smartllm()
        config = slm.config
        model_name = model or config.model
        provider = config.llm_provider

        planner = TaskPlanner(config)
        plan = planner.plan_task(task, model=model_name, provider=provider)
        return format_task_plan(plan)

    except Exception as e:
        return f"Error planning task: {e}"


@mcp.tool()
def token_cache_stats() -> str:
    """Show semantic cache statistics."""
    try:
        slm = _get_smartllm()
        stats = slm.get_cache_report()

        lines = [
            "[Cache Stats]",
            "=" * 40,
            f"Cache enabled:   {slm.config.optimization.enable_cache}",
            f"Total entries:   {stats.get('total_entries', 0)}",
            f"Valid entries:   {stats.get('valid_entries', 0)}",
            f"Expired entries: {stats.get('expired_entries', 0)}",
            f"Cache dir:       {stats.get('cache_dir', 'N/A')}",
            "=" * 40,
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting cache stats: {e}"


@mcp.tool()
def token_session() -> str:
    """Show current session summary including total tokens and cost since server started."""
    try:
        total_tokens = _session["total_input_tokens"] + _session["total_output_tokens"]
        avg_tokens = total_tokens / _session["total_calls"] if _session["total_calls"] > 0 else 0

        lines = [
            "[Session Summary]",
            "=" * 40,
            f"Started:         {_session['started_at']}",
            f"Total calls:     {_session['total_calls']}",
            f"Input tokens:    {_session['total_input_tokens']:,}",
            f"Output tokens:   {_session['total_output_tokens']:,}",
            f"Total tokens:    {total_tokens:,}",
            f"Total cost:      ${_session['total_cost']:.4f}",
            f"Avg tokens/call: {avg_tokens:,.0f}",
            "=" * 40,
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting session: {e}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
