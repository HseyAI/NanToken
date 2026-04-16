import os
import sys
from typing import Dict, Optional, Tuple
from .config import Config, load_config
from .estimator import TokenEstimator, analyze_prompt_complexity, format_token_report
from .clarify import ClarifyingQuestions, build_refined_prompt
from .budget import BudgetManager, BudgetStatus
from .optimizer import PromptOptimizer, estimate_savings
from .integrator import CodeIntegrator


class SmartLLM:
    """Main SmartLLM orchestrator."""
    
    def __init__(self, config: Optional[Config] = None, config_path: Optional[str] = None):
        self.config = config or load_config(config_path)
        
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
        self.integrator = CodeIntegrator()
        
        self.last_estimate = None
        self.last_clarifying_questions = []
        self.last_answers = {}
    
    def analyze(self, prompt: str, system_prompt: str = "") -> Dict:
        """Analyze prompt and return insights."""
        complexity = analyze_prompt_complexity(prompt)
        
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
        
        self.last_estimate = {"estimate": estimate, "cost": cost}
        
        questions = self.clarifier.generate_questions(
            prompt=prompt,
            estimated_tokens=estimate["total_tokens"],
        )
        self.last_clarifying_questions = questions
        
        budget_status = self.budget.get_status()
        
        can_proceed, budget_msg = self.budget.check_request(estimate["total_tokens"])
        
        cached_response = None
        if self.config.optimization.enable_cache:
            cached_response = self.optimizer.check_cache(prompt)
        
        return {
            "complexity": complexity,
            "estimate": estimate,
            "cost": cost,
            "questions": questions,
            "budget_status": budget_status,
            "budget_can_proceed": can_proceed,
            "budget_message": budget_msg,
            "cached_response": cached_response,
        }
    
    def ask_clarifying_questions(self) -> None:
        """Print clarifying questions for user."""
        if not self.last_clarifying_questions:
            print("No clarifying questions needed.")
            return
        
        print(self.clarifier.format_questions(self.last_clarifying_questions))
    
    def get_answers(self, answers: Dict[str, str]) -> str:
        """Process user answers and return refined prompt."""
        self.last_answers = answers
        refined = build_refined_prompt(
            original_prompt="",
            answers=answers,
            system_prompt="",
        )
        return refined
    
    def optimize(self, prompt: str, system_prompt: str = "") -> Dict:
        """Optimize the prompt."""
        if not self.last_estimate:
            self.analyze(prompt, system_prompt)
        
        original_estimate = self.last_estimate["estimate"] if self.last_estimate else {}
        
        optimized_user = self.optimizer.minify_prompt(prompt)
        optimized_system = self.optimizer.minify_prompt(system_prompt) if system_prompt else ""
        
        savings = estimate_savings(prompt, optimized_user)
        
        new_estimate = self.estimator.estimate_request(
            user_prompt=optimized_user,
            system_prompt=optimized_system,
            expected_output_tokens=500,
        )
        
        new_cost = self.estimator.estimate_cost(
            input_tokens=new_estimate["input_tokens"],
            output_tokens=new_estimate["expected_output_tokens"],
            input_price_per_1k=self.config.pricing.input_per_1k,
            output_price_per_1k=self.config.pricing.output_per_1k,
        )
        
        original_cost = self.last_estimate["cost"] if self.last_estimate else new_cost
        
        return {
            "original_prompt": prompt,
            "optimized_prompt": optimized_user,
            "original_estimate": original_estimate,
            "optimized_estimate": new_estimate,
            "savings": savings,
            "cost_reduction": original_cost - new_cost,
        }
    
    def get_budget_report(self) -> str:
        """Get budget status report."""
        status = self.budget.get_status()
        return self.budget.format_status_report(status)
    
    def get_cache_report(self) -> Dict:
        """Get cache statistics."""
        return self.optimizer.get_cache_stats()
    
    def get_project_stats(self) -> Dict:
        """Get project code statistics."""
        return self.integrator.get_project_stats()
    
    def create_code_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = False,
    ) -> Tuple[bool, str]:
        """Create a code file."""
        return self.integrator.create_file(file_path, content, overwrite)
    
    def update_code_file(
        self,
        file_path: str,
        content: str,
        append: bool = False,
    ) -> Tuple[bool, str]:
        """Update a code file."""
        return self.integrator.update_file(file_path, content, append)
    
    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        prompt: str,
        response: Optional[str] = None,
    ) -> None:
        """Record actual usage after LLM call."""
        cost = self.estimator.estimate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_price_per_1k=self.config.pricing.input_per_1k,
            output_price_per_1k=self.config.pricing.output_per_1k,
        )
        self.budget.add_usage(input_tokens, output_tokens, cost, prompt, response)
        
        if self.config.optimization.enable_cache:
            self.optimizer.save_to_cache(prompt, response or "", input_tokens, output_tokens)


def print_analysis_report(analysis: Dict) -> None:
    """Pretty print the analysis report."""
    print("\n" + "=" * 50)
    print("[Analysis] SMARTLLM ANALYSIS REPORT")
    print("=" * 50)
    
    print("\n[Tokens] Token Estimate:")
    est = analysis["estimate"]
    print(f"   Input: {est['input_tokens']:,} tokens")
    print(f"   Output (est): {est['expected_output_tokens']:,} tokens")
    print(f"   Total: {est['total_tokens']:,} tokens")
    print(f"   Cost: ${analysis['cost']:.4f}")
    
    print("\n[Complexity]")
    comp = analysis["complexity"]
    print(f"   Level: {comp['estimated_complexity']}")
    print(f"   Words: {comp['word_count']}")
    print(f"   Code request: {'Yes' if comp['has_code_request'] else 'No'}")
    print(f"   Language specified: {'Yes' if comp['has_language_hint'] else 'No'}")
    
    print("\n[Budget] Budget Status:")
    bs = analysis["budget_status"]
    print(f"   Daily: {bs.daily_used:,}/{bs.daily_limit:,} ({bs.daily_percent:.1f}%)")
    print(f"   Monthly: {bs.monthly_used:,}/{bs.monthly_limit:,} ({bs.monthly_percent:.1f}%)")
    print(f"   Message: {analysis['budget_message']}")
    
    if analysis["questions"]:
        print("\n[Questions] Clarifying Questions:")
        for i, q in enumerate(analysis["questions"], 1):
            print(f"   {i}. {q['question']}")
    
    if analysis["cached_response"]:
        print("\n[Cache] Cache Hit!")
        print(f"   Found cached response from {analysis['cached_response']['cached_at']}")
    
    print("=" * 50)
