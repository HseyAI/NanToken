import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class UsageRecord:
    timestamp: str
    input_tokens: int
    output_tokens: int
    cost: float
    prompt: str
    response: Optional[str] = None


@dataclass 
class BudgetStatus:
    daily_used: int
    daily_limit: int
    monthly_used: int
    monthly_limit: int
    daily_remaining: int
    monthly_remaining: int
    daily_percent: float
    monthly_percent: float
    is_over_budget: bool
    warning_level: str


class BudgetManager:
    """Manage token budget and track usage."""
    
    def __init__(
        self,
        daily_limit: int = 100000,
        monthly_limit: int = 3000000,
        warn_threshold: float = 0.8,
        block_excess: bool = False,
        storage_path: str = ".smartllm_usage.json",
    ):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.warn_threshold = warn_threshold
        self.block_excess = block_excess
        self.storage_path = storage_path
        self.usage_history: list = []
        self._load_usage()
    
    def _load_usage(self) -> None:
        """Load usage history from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self.usage_history = data.get("history", [])
            except:
                self.usage_history = []
    
    def _save_usage(self) -> None:
        """Save usage history to storage (atomic write)."""
        data = {
            "history": self.usage_history,
            "last_updated": datetime.now().isoformat(),
        }
        storage_dir = os.path.dirname(os.path.abspath(self.storage_path))
        os.makedirs(storage_dir, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=storage_dir, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.storage_path)
        except OSError:
            # Fallback to direct write if atomic fails
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
    
    def add_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        prompt: str,
        response: Optional[str] = None,
        project: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Record a usage event."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost,
            "prompt": prompt[:100],
            "response": response[:100] if response else None,
            "project": project,
            "session_id": session_id,
        }
        self.usage_history.append(record)
        self._save_usage()
    
    def get_status(self) -> BudgetStatus:
        """Get current budget status."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        daily_used = sum(
            r["total_tokens"] for r in self.usage_history
            if datetime.fromisoformat(r["timestamp"]) >= today_start
        )
        
        monthly_used = sum(
            r["total_tokens"] for r in self.usage_history
            if datetime.fromisoformat(r["timestamp"]) >= month_start
        )
        
        daily_remaining = max(0, self.daily_limit - daily_used)
        monthly_remaining = max(0, self.monthly_limit - monthly_used)
        
        daily_percent = (daily_used / self.daily_limit) if self.daily_limit > 0 else 0
        monthly_percent = (monthly_used / self.monthly_limit) if self.monthly_limit > 0 else 0
        
        is_over = daily_used > self.daily_limit or monthly_used > self.monthly_limit
        
        if daily_percent >= 1.0 or monthly_percent >= 1.0:
            warning = "critical"
        elif daily_percent >= self.warn_threshold:
            warning = "high"
        elif daily_percent >= self.warn_threshold * 0.7:
            warning = "medium"
        else:
            warning = "none"
        
        return BudgetStatus(
            daily_used=daily_used,
            daily_limit=self.daily_limit,
            monthly_used=monthly_used,
            monthly_limit=self.monthly_limit,
            daily_remaining=daily_remaining,
            monthly_remaining=monthly_remaining,
            daily_percent=daily_percent * 100,
            monthly_percent=monthly_percent * 100,
            is_over_budget=is_over,
            warning_level=warning,
        )
    
    def check_request(
        self,
        estimated_tokens: int,
    ) -> Tuple[bool, str]:
        """Check if request is within budget."""
        status = self.get_status()
        
        if status.is_over_budget:
            return False, "❌ Budget exceeded. Cannot proceed."
        
        if estimated_tokens > status.daily_remaining:
            if self.block_excess:
                return False, f"[X] Request ({estimated_tokens}) exceeds daily remaining ({status.daily_remaining}). Blocked."
            else:
                return True, f"[!] Request will exceed daily budget. Used: {status.daily_used}, Request: {estimated_tokens}, Limit: {status.daily_limit}"
        
        if status.daily_percent >= self.warn_threshold * 100:
            return True, f"[!] Warning: {status.daily_percent:.1f}% of daily budget used. Remaining: {status.daily_remaining:,} tokens"
        
        return True, "[OK] Within budget"
    
    def format_status_report(self, status: Optional[BudgetStatus] = None) -> str:
        """Format budget status as readable report."""
        if status is None:
            status = self.get_status()
        
        icon = "[OK]" if status.warning_level == "none" else "[!]" if status.warning_level in ["medium", "high"] else "[X]"
        
        lines = [
            f"\n{icon} Budget Status:",
            f"  Daily: {status.daily_used:,} / {status.daily_limit:,} ({status.daily_percent:.1f}%)",
            f"  Monthly: {status.monthly_used:,} / {status.monthly_limit:,} ({status.monthly_percent:.1f}%)",
            f"  Remaining today: {status.daily_remaining:,} tokens",
        ]
        
        return "\n".join(lines)
    
    def reset_daily(self) -> None:
        """Reset daily usage (for testing)."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.usage_history = [
            r for r in self.usage_history
            if datetime.fromisoformat(r["timestamp"]) >= today_start
        ]
        self._save_usage()
    
    def get_project_usage(self, days: int = 30, project: Optional[str] = None) -> List[Dict]:
        """Get usage aggregated by project.

        If project is specified, returns daily breakdown for that project.
        Otherwise returns per-project totals.
        """
        now = datetime.now()
        start = now - timedelta(days=days)

        recent = [
            r for r in self.usage_history
            if datetime.fromisoformat(r["timestamp"]) >= start
        ]

        if project:
            recent = [r for r in recent if r.get("project") == project]

        if not recent:
            return []

        if project:
            # Daily breakdown for one project
            by_day: Dict[str, Dict] = {}
            for r in recent:
                day = r["timestamp"][:10]
                if day not in by_day:
                    by_day[day] = {"date": day, "project": project, "total_tokens": 0, "total_cost": 0.0, "call_count": 0}
                by_day[day]["total_tokens"] += r["total_tokens"]
                by_day[day]["total_cost"] += r["cost"]
                by_day[day]["call_count"] += 1
            return sorted(by_day.values(), key=lambda x: x["date"], reverse=True)

        # Aggregate by project
        by_project: Dict[str, Dict] = {}
        for r in recent:
            proj = r.get("project") or "(untagged)"
            if proj not in by_project:
                by_project[proj] = {"project": proj, "total_tokens": 0, "total_cost": 0.0, "call_count": 0}
            by_project[proj]["total_tokens"] += r["total_tokens"]
            by_project[proj]["total_cost"] += r["cost"]
            by_project[proj]["call_count"] += 1
        return sorted(by_project.values(), key=lambda x: x["total_cost"], reverse=True)

    def get_usage_stats(self, days: int = 7) -> Dict:
        """Get usage statistics for the past N days."""
        now = datetime.now()
        start = now - timedelta(days=days)
        
        recent = [
            r for r in self.usage_history
            if datetime.fromisoformat(r["timestamp"]) >= start
        ]
        
        if not recent:
            return {"total_requests": 0, "total_tokens": 0, "total_cost": 0.0, "avg_tokens_per_request": 0}
        
        return {
            "total_requests": len(recent),
            "total_tokens": sum(r["total_tokens"] for r in recent),
            "total_cost": sum(r["cost"] for r in recent),
            "avg_tokens_per_request": sum(r["total_tokens"] for r in recent) / len(recent),
            "avg_cost_per_request": sum(r["cost"] for r in recent) / len(recent),
        }
