import re
import hashlib
import json
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path


class PromptOptimizer:
    """Optimize prompts to reduce token usage."""
    
    def __init__(
        self,
        minify_prompts: bool = True,
        trim_context: bool = True,
        enable_cache: bool = True,
        cache_ttl_hours: int = 24,
        cache_dir: str = ".smartllm_cache",
    ):
        self.minify_prompts = minify_prompts
        self.trim_context = trim_context
        self.enable_cache = enable_cache
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_dir = cache_dir
        self._init_cache()
    
    def _init_cache(self) -> None:
        """Initialize cache storage."""
        if self.enable_cache:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.cache_file = os.path.join(self.cache_dir, "semantic_cache.json")
            self._load_cache()
        else:
            self.cache = {}
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
        else:
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        if self.enable_cache:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def minify_prompt(self, prompt: str) -> str:
        """Remove unnecessary whitespace and shorten prompt."""
        if not self.minify_prompts:
            return prompt
        
        optimized = prompt
        
        optimized = re.sub(r'\n+', '\n', optimized)
        optimized = re.sub(r' +', ' ', optimized)
        optimized = re.sub(r'\t+', ' ', optimized)
        
        optimized = re.sub(r'\*+', '*', optimized)
        optimized = re.sub(r'-+', '-', optimized)
        
        code_block_patterns = [
            (r'```[\w]*\n', '\n```\n'),
            (r'```\n```', ''),
        ]
        
        for pattern, replacement in code_block_patterns:
            optimized = re.sub(pattern, replacement, optimized)
        
        lines = [line.strip() for line in optimized.split('\n') if line.strip()]
        optimized = '\n'.join(lines)
        
        return optimized.strip()
    
    def trim_context(
        self,
        conversation_history: List[Dict[str, str]],
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """Trim conversation history to reduce tokens."""
        if not self.trim_context or not conversation_history:
            return conversation_history
        
        if len(conversation_history) <= max_turns:
            return conversation_history
        
        return conversation_history[-max_turns:]
    
    def summarize_context(
        self,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Generate a summary of past conversation context."""
        if not conversation_history:
            return ""
        
        summaries = []
        for msg in conversation_history[-5:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            summaries.append(f"{role}: {content}")
        
        return "\n".join(summaries)
    
    def check_cache(self, prompt: str) -> Optional[Dict]:
        """Check if there's a cached response for this prompt."""
        if not self.enable_cache:
            return None
        
        cache_key = self._get_cache_key(prompt)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            cached_at = datetime.fromisoformat(entry["cached_at"])
            ttl = timedelta(hours=self.cache_ttl_hours)
            
            if datetime.now() - cached_at < ttl:
                return {
                    "response": entry["response"],
                    "cached_at": entry["cached_at"],
                    "input_tokens": entry.get("input_tokens", 0),
                    "output_tokens": entry.get("output_tokens", 0),
                }
            else:
                del self.cache[cache_key]
                self._save_cache()
        
        return None
    
    def save_to_cache(
        self,
        prompt: str,
        response: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Save response to cache."""
        if not self.enable_cache:
            return
        
        cache_key = self._get_cache_key(prompt)
        
        self.cache[cache_key] = {
            "prompt": prompt[:200],
            "response": response,
            "cached_at": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        self._save_cache()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.enable_cache:
            return {"enabled": False}
        
        valid_entries = 0
        expired_entries = 0
        now = datetime.now()
        ttl = timedelta(hours=self.cache_ttl_hours)
        
        for entry in self.cache.values():
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if now - cached_at < ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "enabled": True,
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_dir": self.cache_dir,
        }
    
    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self.cache = {}
        self._save_cache()
    
    def clear_expired(self) -> None:
        """Clear expired cache entries."""
        now = datetime.now()
        ttl = timedelta(hours=self.cache_ttl_hours)
        
        expired_keys = []
        for key, entry in self.cache.items():
            cached_at = datetime.fromisoformat(entry["cached_at"])
            if now - cached_at >= ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self._save_cache()


def estimate_savings(original: str, optimized: str) -> Dict:
    """Estimate token and cost savings from optimization."""
    orig_tokens = len(original.split()) * 1.3
    opt_tokens = len(optimized.split()) * 1.3
    
    return {
        "original_chars": len(original),
        "optimized_chars": len(optimized),
        "reduction_percent": ((len(original) - len(optimized)) / len(original) * 100) if len(original) > 0 else 0,
        "estimated_token_reduction": int(orig_tokens - opt_tokens),
    }
