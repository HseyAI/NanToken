"""Claude Code Stop hook — auto-tracks real token usage from transcripts.

This script runs after every Claude response via Claude Code's Stop hook.
It parses the session transcript JSONL for actual token counts and cost,
then records them via NanToken's BudgetManager.

Only uses stdlib + BudgetManager (no heavy imports like tiktoken/openai)
to stay under 500ms execution time.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
NANTOKEN_DIR = Path.home() / ".nantoken"
SESSIONS_DIR = NANTOKEN_DIR / "sessions"
USAGE_FILE = NANTOKEN_DIR / "usage.json"

# Minimal pricing table (per 1K tokens) — kept in the hook to avoid heavy imports.
# Covers the models Claude Code typically uses.
PRICING = {
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5": {"input": 0.0008, "output": 0.004},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}
# Default pricing if model not in table
DEFAULT_PRICING = {"input": 0.003, "output": 0.015}


def ensure_dirs() -> None:
    """Create storage directories if missing."""
    NANTOKEN_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def read_hook_input() -> dict:
    """Read JSON payload from stdin (provided by Claude Code)."""
    raw = sys.stdin.read()
    return json.loads(raw)


def load_session_state(session_id: str) -> dict:
    """Load session state or return defaults."""
    path = SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "session_id": session_id,
        "project": None,
        "started_at": datetime.now().isoformat(),
        "last_updated": None,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost": 0.0,
        "call_count": 0,
        "last_transcript_offset": 0,
    }


def save_session_state(session_id: str, state: dict) -> None:
    """Atomic write session state."""
    path = SESSIONS_DIR / f"{session_id}.json"
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(str(tmp_path), str(path))
    except OSError:
        # Fallback
        with open(path, "w") as f:
            json.dump(state, f, indent=2)


def parse_latest_usage(transcript_path: str, last_offset: int) -> tuple:
    """Parse new lines from transcript JSONL, extract the latest message.usage.

    Returns (usage_dict, new_offset) or (None, last_offset) if no new usage.
    usage_dict keys: input_tokens, output_tokens, cache_read_input_tokens,
                     cache_creation_input_tokens, costUSD
    """
    path = Path(transcript_path)
    if not path.exists():
        return None, last_offset

    file_size = path.stat().st_size
    if file_size <= last_offset:
        # File was truncated or no new data
        if file_size < last_offset:
            last_offset = 0  # Reset on truncation
        else:
            return None, last_offset

    try:
        with open(path, "rb") as f:
            f.seek(last_offset)
            new_data = f.read()
            new_offset = f.tell()
    except OSError:
        return None, last_offset

    # Decode and parse lines in reverse (we want the latest usage)
    try:
        lines = new_data.decode("utf-8", errors="replace").strip().split("\n")
    except Exception:
        return None, last_offset

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Try multiple paths where usage data might live
        usage = None
        if isinstance(obj, dict):
            # Path 1: message.usage (most common)
            msg = obj.get("message", {})
            if isinstance(msg, dict) and "usage" in msg:
                usage = msg["usage"]
            # Path 2: top-level usage
            elif "usage" in obj:
                usage = obj["usage"]
            # Path 3: result.usage
            elif "result" in obj and isinstance(obj["result"], dict):
                usage = obj["result"].get("usage")

        if usage and isinstance(usage, dict) and "input_tokens" in usage:
            # Extract model name from the message
            model = ""
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                model = msg.get("model", "")

            # Compute cost from token counts + pricing table
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)

            # Match model to pricing (prefix match for versioned model names)
            prices = DEFAULT_PRICING
            for key, val in PRICING.items():
                if model.startswith(key) or key.startswith(model):
                    prices = val
                    break

            # Total billable input = input + cache_create (cache_read is usually cheaper)
            billable_input = input_tokens + cache_create
            cost = (billable_input / 1000) * prices["input"] + (output_tokens / 1000) * prices["output"]

            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
                "model": model,
                "cost": round(cost, 6),
            }, new_offset

    return None, new_offset


def derive_project(cwd: str) -> str:
    """Derive project name from working directory."""
    return Path(cwd).name if cwd else "(unknown)"


def record_usage(usage: dict, project: str, session_id: str) -> None:
    """Record usage via BudgetManager with centralized storage."""
    # Import here to keep top-level imports lightweight
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from nantoken.budget import BudgetManager

    manager = BudgetManager(storage_path=str(USAGE_FILE))
    manager.add_usage(
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cost=usage.get("cost", 0.0),
        prompt=f"auto:{project}",
        project=project,
        session_id=session_id,
    )


def main() -> None:
    """Entry point for the Stop hook."""
    try:
        ensure_dirs()

        hook_data = read_hook_input()
        session_id = hook_data.get("session_id", "unknown")
        transcript_path = hook_data.get("transcript_path", "")
        cwd = hook_data.get("cwd", "")

        if not transcript_path:
            return

        state = load_session_state(session_id)

        usage, new_offset = parse_latest_usage(
            transcript_path, state["last_transcript_offset"]
        )

        if usage is None:
            return

        project = derive_project(cwd)

        # Record to central usage store
        record_usage(usage, project, session_id)

        # Update session state
        state["project"] = project
        state["last_updated"] = datetime.now().isoformat()
        state["total_input_tokens"] += usage["input_tokens"]
        state["total_output_tokens"] += usage["output_tokens"]
        state["total_cost"] += usage.get("cost", 0.0)
        state["call_count"] += 1
        state["last_transcript_offset"] = new_offset

        save_session_state(session_id, state)

    except Exception:
        # Hook must never crash Claude Code — fail silently
        pass


if __name__ == "__main__":
    main()
