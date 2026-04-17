"""NanToken MCP Server - Token tracking tools for AI coding terminals.

Exposes token estimation, budget tracking, usage analytics, and task planning
as MCP tools that work inside Claude Code, Cursor, Windsurf, and any
MCP-compatible editor.

Usage:
    python -m nantoken              # Start MCP server (stdio)
    mcp run nantoken/mcp_server.py  # Test with MCP CLI
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from nantoken.config import load_config, Config
from nantoken.core import SmartLLM
from nantoken.estimator import TokenEstimator
from nantoken.task_planner import TaskPlanner, format_task_plan

NANTOKEN_DIR = Path.home() / ".nantoken"
SESSIONS_DIR = NANTOKEN_DIR / "sessions"

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
        # Use centralized storage so hook data and MCP tools share the same file
        NANTOKEN_DIR.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        _smartllm.budget.storage_path = str(NANTOKEN_DIR / "usage.json")
        _smartllm.budget._load_usage()
    return _smartllm


def _load_auto_session() -> Optional[dict]:
    """Find the most recently updated auto-tracked session state."""
    if not SESSIONS_DIR.exists():
        return None
    best = None
    best_time = ""
    for f in SESSIONS_DIR.glob("*.json"):
        try:
            with open(f, "r") as fh:
                state = json.load(fh)
            updated = state.get("last_updated") or ""
            if updated > best_time:
                best_time = updated
                best = state
        except (json.JSONDecodeError, OSError):
            continue
    return best


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
        lines = ["[Session Summary]", "=" * 40]

        # Try auto-tracked data first (from Stop hook)
        auto = _load_auto_session()
        if auto and auto.get("call_count", 0) > 0:
            total = auto["total_input_tokens"] + auto["total_output_tokens"]
            avg = total / auto["call_count"] if auto["call_count"] > 0 else 0
            lines.extend([
                f"Source:          auto-tracked (hook active)",
                f"Project:         {auto.get('project', 'N/A')}",
                f"Started:         {auto.get('started_at', 'N/A')}",
                f"Total calls:     {auto['call_count']}",
                f"Input tokens:    {auto['total_input_tokens']:,}",
                f"Output tokens:   {auto['total_output_tokens']:,}",
                f"Total tokens:    {total:,}",
                f"Total cost:      ${auto['total_cost']:.4f}",
                f"Avg tokens/call: {avg:,.0f}",
            ])
        elif _session["total_calls"] > 0:
            # Fall back to manually tracked data
            total = _session["total_input_tokens"] + _session["total_output_tokens"]
            avg = total / _session["total_calls"] if _session["total_calls"] > 0 else 0
            lines.extend([
                f"Source:          manually tracked",
                f"Started:         {_session['started_at']}",
                f"Total calls:     {_session['total_calls']}",
                f"Input tokens:    {_session['total_input_tokens']:,}",
                f"Output tokens:   {_session['total_output_tokens']:,}",
                f"Total tokens:    {total:,}",
                f"Total cost:      ${_session['total_cost']:.4f}",
                f"Avg tokens/call: {avg:,.0f}",
            ])
        else:
            lines.append("No usage recorded yet this session.")
            lines.append("Tip: Install the auto-tracking hook with: python -m nantoken.hooks.install")

        lines.append("=" * 40)
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting session: {e}"


@mcp.tool()
def token_compare(
    prompt: str,
    models: str = "",
) -> str:
    """Compare estimated cost of a prompt across multiple LLM models.

    Shows a side-by-side cost comparison to help pick the right model.

    Args:
        prompt: The prompt text to compare.
        models: Comma-separated model names. Empty = compare all configured models.
    """
    try:
        slm = _get_smartllm()
        estimator = slm.estimator
        pricing = slm.config.pricing

        input_tokens = estimator.count_tokens(prompt)
        expected_output = 500

        # Determine which models to compare
        if models:
            model_list = [m.strip() for m in models.split(",") if m.strip()]
        else:
            model_list = list(pricing.model_pricing.keys())

        if not model_list:
            return "No models configured in pricing. Add models to smartllm.yaml."

        results = []
        for model_name in model_list:
            if model_name in pricing.model_pricing:
                mp = pricing.model_pricing[model_name]
                in_price = mp["input"]
                out_price = mp["output"]
            else:
                continue  # Skip unknown models

            in_cost = (input_tokens / 1000) * in_price
            out_cost = (expected_output / 1000) * out_price
            total = in_cost + out_cost
            results.append((model_name, in_cost, out_cost, total))

        if not results:
            return "None of the specified models found in pricing config."

        # Sort by total cost
        results.sort(key=lambda x: x[3])

        preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
        lines = [
            f"[Cost Comparison] \"{preview}\"",
            f"({input_tokens:,} input tokens + ~{expected_output} output tokens)",
            "=" * 60,
            f"  {'Model':<25} {'Input':>10} {'Output':>10} {'Total':>10}",
            f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}",
        ]

        for name, in_c, out_c, total in results:
            lines.append(
                f"  {name:<25} ${in_c:>8.4f} ${out_c:>8.4f} ${total:>8.4f}"
            )

        cheapest = results[0]
        expensive = results[-1]
        if len(results) > 1 and expensive[3] > 0:
            savings = ((expensive[3] - cheapest[3]) / expensive[3]) * 100
            lines.extend([
                "",
                f"  Cheapest: {cheapest[0]} (${cheapest[3]:.4f})",
                f"  Most expensive: {expensive[0]} (${expensive[3]:.4f})",
                f"  Potential savings: {savings:.0f}%",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)

    except Exception as e:
        return f"Error comparing models: {e}"


@mcp.tool()
def token_history(
    days: int = 7,
    project: str = "",
) -> str:
    """Show token usage history, optionally filtered by project.

    Args:
        days: Number of days to look back (default: 7).
        project: Filter to a specific project name. Empty = show all projects.
    """
    try:
        slm = _get_smartllm()
        records = slm.budget.get_project_usage(
            days=days, project=project or None
        )

        if not records:
            msg = f"No usage recorded in the past {days} days"
            if project:
                msg += f" for project '{project}'"
            msg += "."
            if not project:
                msg += "\nTip: Install the auto-tracking hook to capture per-project data."
            return msg

        if project:
            # Daily breakdown for one project
            lines = [
                f"[Usage History] {project} — last {days} days",
                "=" * 50,
                f"  {'Date':<12} {'Calls':>8} {'Tokens':>12} {'Cost':>10}",
                f"  {'-'*12} {'-'*8} {'-'*12} {'-'*10}",
            ]
            total_tokens = 0
            total_cost = 0.0
            total_calls = 0
            for r in records:
                lines.append(
                    f"  {r['date']:<12} {r['call_count']:>8} "
                    f"{r['total_tokens']:>12,} ${r['total_cost']:>9.4f}"
                )
                total_tokens += r["total_tokens"]
                total_cost += r["total_cost"]
                total_calls += r["call_count"]
            lines.extend([
                f"  {'-'*12} {'-'*8} {'-'*12} {'-'*10}",
                f"  {'Total':<12} {total_calls:>8} {total_tokens:>12,} ${total_cost:>9.4f}",
            ])
        else:
            # Per-project totals
            lines = [
                f"[Usage History] All projects — last {days} days",
                "=" * 55,
                f"  {'Project':<20} {'Calls':>8} {'Tokens':>12} {'Cost':>10}",
                f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10}",
            ]
            total_tokens = 0
            total_cost = 0.0
            total_calls = 0
            for r in records:
                name = r["project"][:20]
                lines.append(
                    f"  {name:<20} {r['call_count']:>8} "
                    f"{r['total_tokens']:>12,} ${r['total_cost']:>9.4f}"
                )
                total_tokens += r["total_tokens"]
                total_cost += r["total_cost"]
                total_calls += r["call_count"]
            lines.extend([
                f"  {'-'*20} {'-'*8} {'-'*12} {'-'*10}",
                f"  {'Total':<20} {total_calls:>8} {total_tokens:>12,} ${total_cost:>9.4f}",
            ])

        lines.append("=" * 55)
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting history: {e}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
