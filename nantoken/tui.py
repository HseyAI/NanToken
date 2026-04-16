import os
import sys
import time
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentTask:
    task_id: int
    description: str
    status: str
    progress: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tokens_used: int = 0
    cost: float = 0.0
    result: str = ""


class PixelTUI:
    """Pixel Agent-style Terminal UI for SmartLLM."""
    
    def __init__(self):
        self.tasks: List[AgentTask] = []
        self.task_counter = 0
        self.session_stats = {
            "total_tasks": 0,
            "completed": 0,
            "failed": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def create_task(self, description: str) -> AgentTask:
        """Create a new task."""
        self.task_counter += 1
        task = AgentTask(
            task_id=self.task_counter,
            description=description,
            status="pending",
            progress=0,
            start_time=None,
        )
        self.tasks.append(task)
        return task
    
    def start_task(self, task_id: int):
        """Mark task as started."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "running"
                task.start_time = datetime.now()
                break
        self._render()
    
    def update_progress(self, task_id: int, progress: int):
        """Update task progress."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.progress = min(100, max(0, progress))
                break
        self._render()
    
    def complete_task(self, task_id: int, result: str = "", tokens: int = 0, cost: float = 0.0):
        """Mark task as completed."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "completed"
                task.progress = 100
                task.end_time = datetime.now()
                task.result = result[:100] + "..." if len(result) > 100 else result
                task.tokens_used = tokens
                task.cost = cost
                self.session_stats["completed"] += 1
                self.session_stats["total_tokens"] += tokens
                self.session_stats["total_cost"] += cost
                break
        self._render()
    
    def fail_task(self, task_id: int, error: str = ""):
        """Mark task as failed."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "failed"
                task.end_time = datetime.now()
                task.result = f"Error: {error}"
                self.session_stats["failed"] += 1
                break
        self._render()
    
    def _render(self):
        """Render the TUI."""
        self.clear_screen()
        
        self._render_header()
        self._render_tasks()
        self._render_footer()
    
    def _render_header(self):
        """Render the header."""
        now = datetime.now().strftime("%H:%M:%S")
        print("=" * 70)
        print(f"  [SmartLLM Agent] - Task Manager")
        print(f"  Time: {now}")
        print("=" * 70)
        print()
    
    def _render_tasks(self):
        """Render all tasks."""
        print("  [Active Tasks]")
        print("  " + "-" * 65)
        
        active_tasks = [t for t in self.tasks if t.status == "running"]
        
        if not active_tasks:
            print("  [No active tasks]")
        else:
            for task in active_tasks:
                self._render_task_row(task)
        
        print()
        print("  [Completed/Failed Tasks]")
        print("  " + "-" * 65)
        
        completed_tasks = [t for t in self.tasks if t.status in ["completed", "failed"]]
        
        if not completed_tasks:
            print("  [No completed tasks]")
        else:
            for task in reversed(completed_tasks[-5:]):
                self._render_task_summary(task)
    
    def _render_task_row(self, task: AgentTask):
        """Render a running task row."""
        duration = ""
        if task.start_time:
            elapsed = (datetime.now() - task.start_time).total_seconds()
            duration = f" ({int(elapsed)}s)"
        
        progress_bar = self._make_progress_bar(task.progress)
        
        desc = task.description[:40] + "..." if len(task.description) > 40 else task.description
        
        print(f"  [{task.task_id:02d}] {desc}{duration}")
        print(f"       {progress_bar} {task.progress}%")
        print()
    
    def _render_task_summary(self, task: AgentTask):
        """Render a completed task summary."""
        status_icon = "[OK]" if task.status == "completed" else "[X]"
        
        duration = ""
        if task.start_time and task.end_time:
            elapsed = (task.end_time - task.start_time).total_seconds()
            duration = f" ({int(elapsed)}s)"
        
        desc = task.description[:35] + "..." if len(task.description) > 35 else task.description
        
        tokens_info = f" | {task.tokens_used:,} tokens" if task.tokens_used else ""
        cost_info = f" | ${task.cost:.4f}" if task.cost else ""
        
        print(f"  {status_icon} [{task.task_id:02d}] {desc}{duration}{tokens_info}{cost_info}")
    
    def _make_progress_bar(self, progress: int, width: int = 30) -> str:
        """Create a progress bar."""
        filled = int(width * progress / 100)
        bar = "=" * filled + "-" * (width - filled)
        return f"[{bar}]"
    
    def _render_footer(self):
        """Render the footer with session stats."""
        print()
        print("=" * 70)
        print(f"  [Session Stats]")
        print(f"  Tasks: {self.session_stats['completed']} completed, {self.session_stats['failed']} failed")
        print(f"  Tokens: {self.session_stats['total_tokens']:,} | Cost: ${self.session_stats['total_cost']:.4f}")
        print("=" * 70)
        print("  Press Ctrl+C to exit")
    
    def animate_thinking(self, task_id: int, messages: List[str]):
        """Animate thinking messages."""
        self.start_task(task_id)
        
        for i, msg in enumerate(messages):
            progress = int((i + 1) / len(messages) * 80)
            self.update_progress(task_id, progress)
            time.sleep(0.5)
        
        self.update_progress(task_id, 90)
    
    def run_with_animation(self, task_description: str, executor_func, *args, **kwargs):
        """Run a task with animation."""
        task = self.create_task(task_description)
        self.session_stats["total_tasks"] += 1
        
        try:
            self.start_task(task.task_id)
            
            result = executor_func(*args, **kwargs)
            
            tokens = kwargs.get("tokens_used", 0)
            cost = kwargs.get("cost", 0.0)
            
            self.complete_task(task.task_id, str(result)[:200], tokens, cost)
            return result
            
        except Exception as e:
            self.fail_task(task.task_id, str(e))
            raise


def demo_tui():
    """Demo the TUI."""
    tui = PixelTUI()
    
    task1 = tui.create_task("Building a REST API with authentication")
    tui.start_task(task1.task_id)
    tui.update_progress(task1.task_id, 30)
    time.sleep(1)
    tui.update_progress(task1.task_id, 60)
    time.sleep(1)
    tui.complete_task(task1.task_id, "REST API created successfully", 1500, 0.045)
    
    task2 = tui.create_task("Analyzing code for bugs")
    tui.start_task(task2.task_id)
    tui.update_progress(task2.task_id, 45)
    time.sleep(1)
    tui.complete_task(task2.task_id, "Found 3 bugs to fix", 800, 0.024)
    
    print("\n[Demo complete. Run with real tasks to see live tracking.]")


if __name__ == "__main__":
    demo_tui()
