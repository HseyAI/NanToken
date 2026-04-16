import os
from typing import Dict, Optional, Tuple, List
import json


class LLMClient:
    """Unified LLM client for multiple providers."""
    
    DEFAULT_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-2.0-flash": {"input": 0.000075, "output": 0.0003},
    }
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: str = "",
        model_pricing: Dict[str, Dict[str, float]] = None,
    ):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_pricing = model_pricing or self.DEFAULT_PRICING
        self._client = None
    
    def _get_openai_client(self):
        """Get OpenAI client."""
        if not self._client:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key or os.getenv("OPENAI_API_KEY"))
            except ImportError:
                raise ImportError("openai package not installed")
        return self._client
    
    def _get_anthropic_client(self):
        """Get Anthropic client."""
        if not self._client:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                raise ImportError("anthropic package not installed")
        return self._client
    
    def _get_gemini_client(self):
        """Get Gemini client."""
        if not self._client:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key or os.getenv("GEMINI_API_KEY"))
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai package not installed")
        return self._client
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost using config-based pricing."""
        model_key = self.model
        
        if model_key in self.model_pricing:
            pricing = self.model_pricing[model_key]
            input_price = pricing.get("input", 0.01)
            output_price = pricing.get("output", 0.03)
        else:
            input_price = 0.01
            output_price = 0.03
        
        return (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Dict:
        """Estimate cost and return breakdown."""
        model_key = self.model
        
        if model_key in self.model_pricing:
            pricing = self.model_pricing[model_key]
            input_price = pricing.get("input", 0.01)
            output_price = pricing.get("output", 0.03)
        else:
            input_price = 0.01
            output_price = 0.03
        
        input_cost = input_tokens / 1000 * input_price
        output_cost = output_tokens / 1000 * output_price
        
        return {
            "model": self.model,
            "provider": self.provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_price_per_1k": input_price,
            "output_price_per_1k": output_price,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }
    
    def call(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Tuple[str, Dict]:
        """
        Call LLM and return (response, usage_info).
        Usage info includes: input_tokens, output_tokens, total_tokens, cost.
        """
        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic" or self.provider == "claude":
            return self._call_anthropic(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "gemini" or self.provider == "google":
            return self._call_gemini(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _call_openai(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict]:
        """Call OpenAI API."""
        client = self._get_openai_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.choices[0].message.content
        usage = response.usage
        
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        
        cost = self.calculate_cost(input_tokens, output_tokens)
        
        usage_info = {
            "provider": "openai",
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
        }
        
        return content, usage_info
    
    def _call_anthropic(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict]:
        """Call Anthropic API."""
        client = self._get_anthropic_client()
        
        messages = [{"role": "user", "content": prompt}]
        
        system = [system_prompt] if system_prompt else []
        
        response = client.messages.create(
            model=self.model,
            system=system,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.content[0].text
        usage = response.usage
        
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        total_tokens = input_tokens + output_tokens
        
        cost = self.calculate_cost(input_tokens, output_tokens)
        
        usage_info = {
            "provider": "anthropic",
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
        }
        
        return content, usage_info
    
    def _call_gemini(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict]:
        """Call Gemini API."""
        client = self._get_gemini_client()
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        model = client.GenerativeModel(self.model)
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = model.generate_content(full_prompt, generation_config=generation_config)
        
        content = response.text
        
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        total_tokens = input_tokens + output_tokens
        
        cost = self.calculate_cost(input_tokens, output_tokens)
        
        usage_info = {
            "provider": "gemini",
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
        }
        
        return content, usage_info


def format_usage_line(usage_info: Dict) -> str:
    """Format usage info as ONE line summary."""
    return (
        f"[Usage] {usage_info['provider'].upper()}/{usage_info['model']} | "
        f"In: {usage_info['input_tokens']} | "
        f"Out: {usage_info['output_tokens']} | "
        f"Total: {usage_info['total_tokens']} | "
        f"Cost: ${usage_info['cost']:.4f}"
    )


def format_usage_summary(total_usage: Dict) -> str:
    """Format total usage summary for multiple calls."""
    calls = total_usage.get("calls", 0)
    return (
        f"[Session] Total: {total_usage.get('total_tokens', 0):,} tokens, "
        f"${total_usage.get('total_cost', 0):.4f} ({calls} calls)"
    )


def format_estimate_report(estimate: Dict) -> str:
    """Format estimate as readable report."""
    return (
        f"[Estimate] {estimate['provider'].upper()}/{estimate['model']} | "
        f"In: {estimate['input_tokens']:,} | "
        f"Out: {estimate['output_tokens']:,} | "
        f"Est. Cost: ${estimate['total_cost']:.4f}"
    )
