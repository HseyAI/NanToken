import os
import sys
import time
from typing import Dict, Optional, List
from pathlib import Path

from nantoken.config import Config, load_config
from nantoken.estimator import TokenEstimator
from nantoken.clarify import ClarifyingQuestions
from nantoken.budget import BudgetManager
from nantoken.optimizer import PromptOptimizer
from nantoken.llm_client import LLMClient, format_usage_line, format_usage_summary, format_estimate_report
from nantoken.task_planner import TaskPlanner, format_task_plan, format_task_ask
from nantoken.tui import PixelTUI


class SmartLLMRunner:
    """Run actual LLM calls with SmartLLM optimization and tracking."""
    
    def __init__(self, config: Optional[Config] = None, config_path: str = "smartllm.yaml"):
        self.config = config or load_config(config_path)
        self.llm = LLMClient(
            provider=self.config.llm_provider,
            model=self.config.model,
            api_key=self.config.api_key,
            model_pricing=self.config.pricing.model_pricing,
        )
        self.estimator = TokenEstimator(model=self.config.model)
        self.clarifier = ClarifyingQuestions(
            enabled=self.config.clarifying_questions.enabled,
            always_ask=self.config.clarifying_questions.always_ask,
            threshold_tokens=self.config.clarifying_questions.threshold_tokens,
        )
        self.budget = BudgetManager(
            daily_limit=self.config.budget.daily_limit,
            monthly_limit=self.config.budget.monthly_limit,
            warn_threshold=self.config.budget.warn_threshold,
            block_excess=self.config.budget.block_excess,
        )
        self.optimizer = PromptOptimizer(
            minify_prompts=self.config.optimization.minify_prompts,
            trim_context=self.config.optimization.trim_context,
            enable_cache=self.config.optimization.enable_cache,
            cache_ttl_hours=self.config.optimization.cache_ttl_hours,
            cache_dir=self.config.cache_dir,
        )
        self.task_planner = TaskPlanner(self.llm)
        self.tui = PixelTUI()
        
        self.session_usage = {
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_input": 0,
            "total_output": 0,
            "calls": 0,
        }
    
    def run(
        self,
        prompt: str,
        system_prompt: str = "",
        show_estimate: bool = True,
        auto_optimize: bool = True,
        max_tokens: int = 2000,
        use_tui: bool = False,
    ) -> str:
        """Run LLM with SmartLLM optimization and tracking."""
        if use_tui:
            return self._run_with_tui(prompt, system_prompt, show_estimate, auto_optimize, max_tokens)
        
        if show_estimate:
            self._show_estimate(prompt, system_prompt)
        
        cached_response = None
        if self.config.optimization.enable_cache:
            cached_response = self.optimizer.check_cache(prompt)
            if cached_response:
                print(f"\n[CACHE] Found cached response")
                print(cached_response["response"])
                print(format_usage_line({
                    "provider": "cache",
                    "model": "cached",
                    "input_tokens": cached_response.get("input_tokens", 0),
                    "output_tokens": cached_response.get("output_tokens", 0),
                    "total_tokens": cached_response.get("input_tokens", 0) + cached_response.get("output_tokens", 0),
                    "cost": 0,
                }))
                return cached_response["response"]
        
        optimized_prompt = prompt
        if auto_optimize:
            optimized_prompt = self.optimizer.minify_prompt(prompt)
        
        try:
            response, usage = self.llm.call(
                prompt=optimized_prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
            )
            
            print(f"\n{response}")
            
            print(format_usage_line(usage))
            
            self._update_session_usage(usage)
            self.budget.add_usage(
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cost=usage["cost"],
                prompt=prompt,
                response=response,
            )
            
            if self.config.optimization.enable_cache:
                self.optimizer.save_to_cache(
                    prompt=prompt,
                    response=response,
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                )
            
            return response
            
        except Exception as e:
            print(f"[Error] {str(e)}")
            return ""
    
    def _run_with_tui(
        self,
        prompt: str,
        system_prompt: str,
        show_estimate: bool,
        auto_optimize: bool,
        max_tokens: int,
    ) -> str:
        """Run with TUI animation."""
        task = self.tui.create_task(prompt[:50])
        self.session_usage["calls"] += 1
        
        self.tui.start_task(task.task_id)
        self.tui.update_progress(task.task_id, 10)
        
        if show_estimate:
            estimate = self.estimator.estimate_request(prompt, system_prompt, 500)
            est_cost = self.estimator.estimate_cost(
                estimate["input_tokens"],
                estimate["expected_output_tokens"],
                self.config.pricing.input_per_1k,
                self.config.pricing.output_per_1k,
            )
            print(format_estimate_report({
                "provider": self.config.llm_provider,
                "model": self.config.model,
                "input_tokens": estimate["input_tokens"],
                "output_tokens": estimate["expected_output_tokens"],
                "total_cost": est_cost,
            }))
            time.sleep(1)
        
        self.tui.update_progress(task.task_id, 30)
        
        cached_response = None
        if self.config.optimization.enable_cache:
            cached_response = self.optimizer.check_cache(prompt)
        
        if cached_response:
            self.tui.update_progress(task.task_id, 100)
            self.tui.complete_task(
                task.task_id, 
                cached_response["response"][:100],
                cached_response.get("input_tokens", 0),
                0
            )
            print(f"\n[CACHE] {cached_response['response']}")
            return cached_response["response"]
        
        optimized_prompt = self.optimizer.minify_prompt(prompt) if auto_optimize else prompt
        
        try:
            self.tui.update_progress(task.task_id, 50)
            response, usage = self.llm.call(optimized_prompt, system_prompt, max_tokens=max_tokens)
            
            self.tui.update_progress(task.task_id, 80)
            
            print(f"\n{response}")
            print(format_usage_line(usage))
            
            self.tui.complete_task(
                task.task_id,
                response[:100],
                usage["total_tokens"],
                usage["cost"]
            )
            
            self._update_session_usage(usage)
            self.budget.add_usage(usage["input_tokens"], usage["output_tokens"], usage["cost"], prompt, response)
            
            if self.config.optimization.enable_cache:
                self.optimizer.save_to_cache(prompt, response, usage["input_tokens"], usage["output_tokens"])
            
            return response
            
        except Exception as e:
            self.tui.fail_task(task.task_id, str(e))
            print(f"\n[Error] {str(e)}")
            return ""
    
    def run_with_plan(self, prompt: str, auto_confirm: bool = False) -> str:
        """Plan a task, show forecast, then execute."""
        plan = self.task_planner.plan_task(
            task=prompt,
            model=self.config.model,
            provider=self.config.llm_provider,
        )
        
        print(format_task_plan(plan))
        
        if auto_confirm:
            confirm = "y"
        else:
            confirm = input(format_task_ask(plan)).strip().lower()
        
        if confirm not in ["", "y", "yes"]:
            print("[Cancelled]")
            return ""
        
        budget_ok, budget_msg = self.budget.check_request(plan.total_estimated_tokens)
        
        if not budget_ok or "exceed" in budget_msg.lower():
            print(f"[Budget] {budget_msg}")
            confirm2 = input("Continue anyway? [y/n]: ").strip().lower()
            if confirm2 not in ["y", "yes"]:
                return ""
        
        print("\n[Executing...]")
        return self.run(prompt, use_tui=True)
    
    def _show_estimate(self, prompt: str, system_prompt: str = ""):
        """Show token estimate before calling LLM."""
        estimate = self.estimator.estimate_request(
            user_prompt=prompt,
            system_prompt=system_prompt,
            expected_output_tokens=500,
        )
        
        cost = self.estimator.estimate_cost(
            input_tokens=estimate["input_tokens"],
            output_tokens=estimate["expected_output_tokens"],
            input_price_per_1k=self.config.pricing.input_per_1k,
            output_price_per_1k=self.config.pricing.output_per_1k,
        )
        
        budget_status = self.budget.get_status()
        
        print("\n" + "=" * 50)
        print("[Estimate] Before calling LLM:")
        print(f"  Model: {self.config.llm_provider}/{self.config.model}")
        print(f"  Input: {estimate['input_tokens']} tokens")
        print(f"  Output (est): {estimate['expected_output_tokens']} tokens")
        print(f"  Total: {estimate['total_tokens']} tokens")
        print(f"  Cost (est): ${cost:.4f}")
        print(f"  Daily budget: {budget_status.daily_used}/{budget_status.daily_limit} ({budget_status.daily_percent:.1f}%)")
        print("=" * 50 + "\n")
    
    def _update_session_usage(self, usage: Dict):
        """Update session usage tracking."""
        self.session_usage["total_tokens"] += usage["total_tokens"]
        self.session_usage["total_cost"] += usage["cost"]
        self.session_usage["total_input"] += usage["input_tokens"]
        self.session_usage["total_output"] += usage["output_tokens"]
    
    def session_summary(self) -> str:
        """Get session usage summary."""
        return format_usage_summary(self.session_usage)
    
    def interactive_mode(self):
        """Run interactive mode with the LLM."""
        print("\n" + "=" * 50)
        print("[SmartLLM] Interactive Mode")
        print(f"Provider: {self.config.llm_provider}/{self.config.model}")
        print("Commands: 'plan <task>' for task planning, 'tui' for TUI mode")
        print("Type 'exit' to quit, 'summary' for stats")
        print("=" * 50 + "\n")
        
        while True:
            try:
                prompt = input("> ").strip()
                if not prompt:
                    continue
                
                if prompt.lower() in ["exit", "quit"]:
                    print(f"\n{self.session_summary()}")
                    print("[Done]")
                    break
                
                if prompt.lower() == "summary":
                    print(f"\n{self.session_summary()}\n")
                    continue
                
                if prompt.lower() == "budget":
                    status = self.budget.get_status()
                    print(self.budget.format_status_report(status))
                    continue
                
                if prompt.lower() == "tui":
                    print("[TUI Mode] Use 'run <prompt> --tui'")
                    continue
                
                if prompt.lower().startswith("plan "):
                    task = prompt[5:]
                    self.run_with_plan(task)
                    continue
                
                self.run(prompt)
                
            except KeyboardInterrupt:
                print(f"\n{self.session_summary()}")
                break
            except EOFError:
                break


def run_from_cli():
    """CLI entry point for running LLM calls."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SmartLLM - Run LLM with optimization")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to LLM")
    parser.add_argument("-c", "--config", default="smartllm.yaml", help="Config file")
    parser.add_argument("-s", "--system", default="", help="System prompt")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("-f", "--file", help="Read prompt from file")
    parser.add_argument("--tui", action="store_true", help="Use TUI mode")
    parser.add_argument("--plan", action="store_true", help="Plan task before running")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    runner = SmartLLMRunner(config, args.config)
    
    if args.interactive:
        runner.interactive_mode()
    elif args.file:
        with open(args.file, "r") as f:
            prompt = f.read()
        runner.run(prompt, args.system, use_tui=args.tui)
    elif args.prompt:
        if args.plan:
            runner.run_with_plan(args.prompt)
        else:
            runner.run(args.prompt, args.system, use_tui=args.tui)
    else:
        print("Usage: smartllm run 'prompt' or smartllm run --plan 'build a website'")


if __name__ == "__main__":
    run_from_cli()
