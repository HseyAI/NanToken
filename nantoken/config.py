import json
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class BudgetConfig:
    daily_limit: int = 100000
    monthly_limit: int = 3000000
    warn_threshold: float = 0.8
    block_excess: bool = False


@dataclass
class PricingConfig:
    input_per_1k: float = 0.01
    output_per_1k: float = 0.03
    model_pricing: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "gemini-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    })


@dataclass
class OptimizationConfig:
    minify_prompts: bool = True
    trim_context: bool = True
    enable_cache: bool = True
    cache_ttl_hours: int = 24


@dataclass
class ClarifyingQuestionsConfig:
    enabled: bool = True
    always_ask: bool = False
    threshold_tokens: int = 500


@dataclass
class Config:
    llm_provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    pricing: PricingConfig = field(default_factory=PricingConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    clarifying_questions: ClarifyingQuestionsConfig = field(default_factory=ClarifyingQuestionsConfig)
    cache_dir: str = ".smartllm_cache"
    log_level: str = "INFO"


DEFAULT_CONFIG = Config()


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or return defaults."""
    if config_path is None:
        config_path = os.path.join(os.getcwd(), "smartllm.yaml")
    
    if not os.path.exists(config_path):
        return DEFAULT_CONFIG
    
    with open(config_path, "r") as f:
        if config_path.endswith(".yaml") or config_path.endswith(".yml"):
            data = yaml.safe_load(f)
        else:
            data = json.load(f)
    
    return _parse_config(data)


def _parse_config(data: Dict[str, Any]) -> Config:
    """Parse configuration dictionary into Config object."""
    budget = BudgetConfig(**data.get("budget", {}))
    pricing = PricingConfig(**data.get("pricing", {}))
    optimization = OptimizationConfig(**data.get("optimization", {}))
    clarifying_questions = ClarifyingQuestionsConfig(**data.get("clarifying_questions", {}))
    
    return Config(
        llm_provider=data.get("llm_provider", "openai"),
        model=data.get("model", "gpt-4"),
        api_key=data.get("api_key", ""),
        budget=budget,
        pricing=pricing,
        optimization=optimization,
        clarifying_questions=clarifying_questions,
        cache_dir=data.get("cache_dir", ".smartllm_cache"),
        log_level=data.get("log_level", "INFO"),
    )


def save_config(config: Config, config_path: str = "smartllm.yaml") -> None:
    """Save configuration to file."""
    data = {
        "llm_provider": config.llm_provider,
        "model": config.model,
        "api_key": config.api_key,
        "budget": {
            "daily_limit": config.budget.daily_limit,
            "monthly_limit": config.budget.monthly_limit,
            "warn_threshold": config.budget.warn_threshold,
            "block_excess": config.budget.block_excess,
        },
        "pricing": {
            "input_per_1k": config.pricing.input_per_1k,
            "output_per_1k": config.pricing.output_per_1k,
            "model_pricing": config.pricing.model_pricing,
        },
        "optimization": {
            "minify_prompts": config.optimization.minify_prompts,
            "trim_context": config.optimization.trim_context,
            "enable_cache": config.optimization.enable_cache,
            "cache_ttl_hours": config.optimization.cache_ttl_hours,
        },
        "clarifying_questions": {
            "enabled": config.clarifying_questions.enabled,
            "always_ask": config.clarifying_questions.always_ask,
            "threshold_tokens": config.clarifying_questions.threshold_tokens,
        },
        "cache_dir": config.cache_dir,
        "log_level": config.log_level,
    }
    
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def create_default_config(path: str = "smartllm.yaml") -> None:
    """Create a default configuration file."""
    save_config(DEFAULT_CONFIG, path)
