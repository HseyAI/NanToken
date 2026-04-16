from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TaskStep:
    step_number: int
    description: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    notes: str = ""


@dataclass
class TaskPlan:
    task: str
    provider: str
    model: str
    steps: List[TaskStep]
    total_estimated_input: int
    total_estimated_output: int
    total_estimated_tokens: int
    estimated_cost: float
    complexity: str
    reasoning: str


class TaskPlanner:
    """Plan complex tasks with token forecasting and reasoning."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def plan_task(self, task: str, model: str = "gpt-4", provider: str = "openai") -> TaskPlan:
        """Analyze a task and create a plan with token estimates."""
        task_lower = task.lower()
        
        steps = []
        
        if self._is_code_generation(task_lower):
            steps = self._plan_code_generation(task)
        elif self._is_website_builder(task_lower):
            steps = self._plan_website_builder(task)
        elif self._is_debugging(task_lower):
            steps = self._plan_debugging(task)
        elif self._is_data_analysis(task_lower):
            steps = self._plan_data_analysis(task)
        elif self._is_documentation(task_lower):
            steps = self._plan_documentation(task)
        elif self._is_api_integration(task_lower):
            steps = self._plan_api_integration(task)
        else:
            steps = self._plan_general_task(task)
        
        total_input = sum(s.estimated_input_tokens for s in steps)
        total_output = sum(s.estimated_output_tokens for s in steps)
        
        complexity = self._determine_complexity(total_input, total_output)
        
        reasoning = self._generate_reasoning(task, steps, complexity)
        
        estimated_cost = self._estimate_cost(total_input, total_output, model, provider)
        
        return TaskPlan(
            task=task,
            provider=provider,
            model=model,
            steps=steps,
            total_estimated_input=total_input,
            total_estimated_output=total_output,
            total_estimated_tokens=total_input + total_output,
            estimated_cost=estimated_cost,
            complexity=complexity,
            reasoning=reasoning,
        )
    
    def _is_code_generation(self, task: str) -> bool:
        keywords = ["write", "create", "implement", "function", "class", "script", "code"]
        return any(kw in task for kw in keywords)
    
    def _is_website_builder(self, task: str) -> bool:
        keywords = ["website", "web page", "html", "css", "frontend", "landing page", "webapp"]
        return any(kw in task for kw in keywords)
    
    def _is_debugging(self, task: str) -> bool:
        keywords = ["debug", "fix", "error", "bug", "issue", "problem", "not working"]
        return any(kw in task for kw in keywords)
    
    def _is_data_analysis(self, task: str) -> bool:
        keywords = ["analyze", "data", "chart", "graph", "visualization", "report", "statistics"]
        return any(kw in task for kw in keywords)
    
    def _is_documentation(self, task: str) -> bool:
        keywords = ["document", "docs", "readme", "explain", "tutorial", "guide"]
        return any(kw in task for kw in keywords)
    
    def _is_api_integration(self, task: str) -> bool:
        keywords = ["api", "integrate", "connect", "endpoint", "rest", "webhook"]
        return any(kw in task for kw in keywords)
    
    def _plan_code_generation(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Analyze requirements and determine code structure", 100, 200, "Understanding what to build"),
            TaskStep(2, "Generate core implementation code", 300, 800, "Main logic generation"),
            TaskStep(3, "Add comments and documentation", 100, 300, "Code explanation"),
            TaskStep(4, "Review and refine output", 150, 200, "Quality check"),
        ]
    
    def _plan_website_builder(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Analyze requirements and plan structure", 150, 300, "Understanding UI/UX needs"),
            TaskStep(2, "Generate HTML structure", 200, 500, "Page layout"),
            TaskStep(3, "Generate CSS styling", 200, 600, "Visual design"),
            TaskStep(4, "Add JavaScript functionality", 150, 400, "Interactivity"),
            TaskStep(5, "Review and optimize code", 100, 200, "Quality check"),
        ]
    
    def _plan_debugging(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Analyze the problem description", 100, 150, "Understanding the issue"),
            TaskStep(2, "Identify potential causes", 200, 300, "Root cause analysis"),
            TaskStep(3, "Generate fix suggestions", 200, 400, "Solution proposals"),
            TaskStep(4, "Provide corrected code", 150, 300, "Final solution"),
        ]
    
    def _plan_data_analysis(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Understand data requirements", 100, 150, "What to analyze"),
            TaskStep(2, "Plan analysis approach", 150, 200, "Methodology"),
            TaskStep(3, "Generate analysis code", 300, 500, "Implementation"),
            TaskStep(4, "Summarize findings", 100, 300, "Results"),
        ]
    
    def _plan_documentation(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Understand the subject to document", 150, 200, "Content gathering"),
            TaskStep(2, "Structure the documentation", 100, 150, "Outline creation"),
            TaskStep(3, "Generate documentation content", 200, 800, "Main content"),
            TaskStep(4, "Format and refine", 50, 150, "Final polish"),
        ]
    
    def _plan_api_integration(self, task: str) -> List[TaskStep]:
        return [
            TaskStep(1, "Analyze API requirements", 150, 200, "Understanding endpoints"),
            TaskStep(2, "Plan integration approach", 200, 300, "Architecture"),
            TaskStep(3, "Generate integration code", 300, 600, "Implementation"),
            Step(4, "Add error handling and testing", 150, 300, "Robustness"),
        ]
    
    def _plan_general_task(self, task: str) -> List[TaskStep]:
        word_count = len(task.split())
        if word_count < 10:
            return [
                TaskStep(1, "Process the request", 50, 200, "Simple task"),
            ]
        elif word_count < 30:
            return [
                TaskStep(1, "Analyze request", 100, 150, "Understanding"),
                TaskStep(2, "Generate response", 150, 400, "Main output"),
                TaskStep(3, "Refine and finalize", 50, 100, "Polish"),
            ]
        else:
            return [
                TaskStep(1, "Analyze requirements in detail", 200, 300, "Deep understanding"),
TaskStep(2, "Plan approach", 150, 200, "Strategy"),
            TaskStep(3, "Execute main task", 300, 600, "Implementation"),
                Step(4, "Review and refine", 100, 200, "Quality"),
            ]
    
    def _determine_complexity(self, input_tokens: int, output_tokens: int) -> str:
        total = input_tokens + output_tokens
        if total < 500:
            return "Simple"
        elif total < 1500:
            return "Medium"
        elif total < 3000:
            return "Complex"
        else:
            return "Very Complex"
    
    def _generate_reasoning(self, task: str, steps: List[TaskStep], complexity: str) -> str:
        task_type = self._identify_task_type(task)
        return f"This {complexity.lower()} {task_type} task will require {len(steps)} steps to complete. Each step builds on the previous to deliver the final result."
    
    def _identify_task_type(self, task: str) -> str:
        task_lower = task.lower()
        if self._is_code_generation(task_lower):
            return "code generation"
        elif self._is_website_builder(task_lower):
            return "website building"
        elif self._is_debugging(task_lower):
            return "debugging"
        elif self._is_data_analysis(task_lower):
            return "data analysis"
        elif self._is_documentation(task_lower):
            return "documentation"
        elif self._is_api_integration(task_lower):
            return "API integration"
        else:
            return "general"
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str, provider: str) -> float:
        pricing = {
            "gpt-4": (0.03, 0.06),
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            "claude-3-5-sonnet": (0.003, 0.015),
            "claude-3-haiku": (0.00025, 0.00125),
            "gemini-1.5-flash": (0.000075, 0.0003),
        }
        
        input_price, output_price = pricing.get(model, (0.01, 0.03))
        return (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)


def format_task_plan(plan: TaskPlan) -> str:
    """Format task plan as readable report."""
    lines = [
        "",
        "=" * 60,
        f"[Task Plan] {plan.task[:50]}..." if len(plan.task) > 50 else f"[Task Plan] {plan.task}",
        "=" * 60,
        f"Model: {plan.provider.upper()}/{plan.model}",
        f"Complexity: {plan.complexity}",
        "",
        "[Reasoning]",
        plan.reasoning,
        "",
        "[Steps]",
    ]
    
    for step in plan.steps:
        lines.append(f"  {step.step_number}. {step.description}")
        lines.append(f"     Est: {step.estimated_input_tokens + step.estimated_output_tokens} tokens ({step.notes})")
    
    lines.extend([
        "",
        "[Forecast]",
        f"  Total Input:  {plan.total_estimated_input:,} tokens",
        f"  Total Output: {plan.total_estimated_output:,} tokens",
        f"  Total:        {plan.total_estimated_tokens:,} tokens",
        f"  Est. Cost:    ${plan.estimated_cost:.4f}",
        "=" * 60,
    ])
    
    return "\n".join(lines)


def format_task_ask(plan: TaskPlan) -> str:
    """Format the confirmation question."""
    return (
        f"\n[Confirm] This {plan.complexity.lower()} task will use ~{plan.total_estimated_tokens:,} tokens "
        f"(~${plan.estimated_cost:.4f}). Proceed? [Y/n]: "
    )
