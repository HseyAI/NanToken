import re
from typing import Dict, Tuple, Optional
import tiktoken


class TokenEstimator:
    """Estimate token counts for LLM requests."""
    
    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self.encoding = self._get_encoding()
        
        self.model_context_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-3.5-turbo": 16385,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-5-sonnet": 200000,
            "gemini-pro": 32000,
            "gemini-1.5-pro": 1000000,
        }
    
    def _get_encoding(self):
        """Get encoding for the model."""
        try:
            if "gpt" in self.model:
                return tiktoken.encoding_for_model("gpt-4")
            else:
                return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_messages_tokens(self, messages: list) -> int:
        """Count tokens for a list of messages."""
        total = 0
        for msg in messages:
            total += self.count_tokens(msg.get("content", ""))
            total += 4
        total += 2
        return total
    
    def estimate_request(
        self,
        user_prompt: str,
        system_prompt: str = "",
        expected_output_tokens: int = 500,
    ) -> Dict[str, int]:
        """Estimate tokens for a complete request."""
        input_tokens = self.count_tokens(system_prompt) + self.count_tokens(user_prompt)
        
        return {
            "input_tokens": input_tokens,
            "expected_output_tokens": expected_output_tokens,
            "total_tokens": input_tokens + expected_output_tokens,
            "system_prompt_tokens": self.count_tokens(system_prompt),
            "user_prompt_tokens": self.count_tokens(user_prompt),
        }
    
    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        input_price_per_1k: float = 0.01,
        output_price_per_1k: float = 0.03,
    ) -> float:
        """Estimate cost in USD."""
        input_cost = (input_tokens / 1000) * input_price_per_1k
        output_cost = (output_tokens / 1000) * output_price_per_1k
        return input_cost + output_cost
    
    def get_context_limit(self) -> int:
        """Get context window limit for current model."""
        for key, limit in self.model_context_limits.items():
            if key in self.model.lower():
                return limit
        return 8192
    
    def check_context_limit(self, input_tokens: int) -> Tuple[bool, str]:
        """Check if request exceeds context limit."""
        limit = self.get_context_limit()
        if input_tokens > limit:
            return False, f"Exceeds context limit ({limit} tokens). Need to truncate."
        elif input_tokens > limit * 0.9:
            return False, f"Near context limit ({limit} tokens). Consider truncating."
        return True, "Within context limit"


def format_token_report(estimate: Dict[str, int], cost: float) -> str:
    """Format token estimate as readable report."""
    lines = [
        "Token Estimate:",
        f"  • Input tokens: {estimate['input_tokens']:,}",
        f"  • Expected output: {estimate['expected_output_tokens']:,}",
        f"  • Total: {estimate['total_tokens']:,}",
        f"  • Estimated cost: ${cost:.4f}",
    ]
    return "\n".join(lines)


def analyze_prompt_complexity(prompt: str) -> Dict[str, any]:
    """Analyze prompt to determine complexity and ambiguity."""
    words = prompt.split()
    sentences = re.split(r'[.!?]+', prompt)
    
    has_code_keywords = any(
        kw in prompt.lower() 
        for kw in ["write", "code", "function", "implement", "class", "algorithm"]
    )
    
    has_language_hint = any(
        lang in prompt.lower() 
        for lang in ["python", "javascript", "java", "c++", "go", "rust", "ruby"]
    )
    
    has_format_hint = any(
        fmt in prompt.lower() 
        for fmt in ["json", "xml", "csv", "markdown", "table", "list"]
    )
    
    is_ambiguous = (
        len(words) < 10 or
        "or" in prompt.lower() or
        ("which" in prompt.lower() and "?" in prompt)
    )
    
    return {
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "has_code_request": has_code_keywords,
        "has_language_hint": has_language_hint,
        "has_format_hint": has_format_hint,
        "is_ambiguous": is_ambiguous,
        "estimated_complexity": "high" if len(words) > 50 else "medium" if len(words) > 20 else "low",
    }
