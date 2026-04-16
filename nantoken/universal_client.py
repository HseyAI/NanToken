import os
import json
from typing import Dict, Optional, Tuple
import requests


class UniversalLLMClient:
    """Universal LLM client that works with ANY model/provider."""
    
    DEFAULT_PROVIDERS = {
        "openai": {
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model_key": "model",
            "messages_key": "messages",
            "response_format": "chat",
        },
        "anthropic": {
            "endpoint": "https://api.anthropic.com/v1/messages",
            "model_key": "model",
            "messages_key": "messages",
            "headers": {"x-api-key": "REQUIRED", "anthropic-version": "2023-06-01"},
            "response_format": "chat",
        },
        "gemini": {
            "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            "model_key": "model",
            "prompt_key": "contents",
            "response_format": "gemini",
        },
    }
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        api_key: str = "",
        endpoint: str = "",
        custom_headers: Dict = None,
        pricing: Dict[str, Dict[str, float]] = None,
    ):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint
        self.custom_headers = custom_headers or {}
        self.pricing = pricing or {}
        
        self._setup_provider()
    
    def _setup_provider(self):
        """Setup provider configuration."""
        if self.provider in self.DEFAULT_PROVIDERS:
            config = self.DEFAULT_PROVIDERS[self.provider]
            if not self.endpoint:
                self.endpoint = config.get("endpoint", "")
            if not self.custom_headers:
                self.custom_headers = config.get("headers", {})
        
        if not self.endpoint:
            self.endpoint = os.getenv("LLM_ENDPOINT", "")
        
        if not self.api_key:
            env_key = f"{self.provider.upper()}_API_KEY"
            self.api_key = os.getenv(env_key, "")
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost using config-based pricing."""
        model_key = self.model
        
        if model_key in self.pricing:
            pricing = self.pricing[model_key]
            input_price = pricing.get("input", 0.01)
            output_price = pricing.get("output", 0.03)
        elif self.provider in self.pricing:
            pricing = self.pricing[self.provider]
            input_price = pricing.get("input", 0.01)
            output_price = pricing.get("output", 0.03)
        else:
            input_price = 0.01
            output_price = 0.03
        
        return (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
    
    def call(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Tuple[str, Dict]:
        """Call the LLM and return response with usage info."""
        if self.provider in ["openai", "ollama", "lmstudio", "kimi", "qwen", "deepseek", "custom"]:
            return self._call_openai_style(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "gemini":
            return self._call_gemini(prompt, system_prompt, temperature, max_tokens)
        else:
            return self._call_custom(prompt, system_prompt, temperature, max_tokens)
    
    def _call_openai_style(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict]:
        """Call OpenAI-compatible API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        headers.update(self.custom_headers)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=data,
            timeout=120,
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", len(prompt.split()) * 1.3)
            output_tokens = usage.get("completion_tokens", len(content.split()) * 1.3)
        elif "content" in result:
            content = result["content"]
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(content.split()) * 1.3
        else:
            content = str(result)
            input_tokens = len(prompt.split()) * 1.3
            output_tokens = len(content.split()) * 1.3
        
        total_tokens = int(input_tokens + output_tokens)
        cost = self.calculate_cost(int(input_tokens), int(output_tokens))
        
        usage_info = {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
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
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        
        messages = [{"role": "user", "content": prompt}]
        
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if system_prompt:
            data["system"] = [system_prompt]
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=data,
            timeout=120,
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        content = result["content"][0]["text"]
        usage = result.get("usage", {})
        
        input_tokens = usage.get("input_tokens", len(prompt.split()) * 1.3)
        output_tokens = usage.get("output_tokens", len(content.split()) * 1.3)
        
        total_tokens = int(input_tokens + output_tokens)
        cost = self.calculate_cost(int(input_tokens), int(output_tokens))
        
        usage_info = {
            "provider": "anthropic",
            "model": self.model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
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
        headers = {"Content-Type": "application/json"}
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        endpoint = self.endpoint.format(model=self.model)
        
        data = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        
        if self.api_key:
            endpoint += f"?key={self.api_key}"
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=data,
            timeout=120,
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        result = response.json()
        
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        
        usage = result.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", len(prompt.split()) * 1.3)
        output_tokens = usage.get("candidatesTokenCount", len(content.split()) * 1.3)
        
        total_tokens = int(input_tokens + output_tokens)
        cost = self.calculate_cost(int(input_tokens), int(output_tokens))
        
        usage_info = {
            "provider": "gemini",
            "model": self.model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "total_tokens": total_tokens,
            "cost": cost,
        }
        
        return content, usage_info
    
    def _call_custom(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict]:
        """Call custom/other LLM APIs."""
        return self._call_openai_style(prompt, system_prompt, temperature, max_tokens)


class UniversalLLM:
    """Wrapper for backward compatibility."""
    
    def __init__(self, provider="openai", model="gpt-4", api_key="", **kwargs):
        pricing = kwargs.get("model_pricing", {})
        self.client = UniversalLLMClient(
            provider=provider,
            model=model,
            api_key=api_key,
            endpoint=kwargs.get("endpoint", ""),
            custom_headers=kwargs.get("custom_headers", {}),
            pricing=pricing,
        )
    
    def call(self, prompt, system_prompt="", temperature=0.7, max_tokens=2000):
        return self.client.call(prompt, system_prompt, temperature, max_tokens)
    
    def calculate_cost(self, input_tokens, output_tokens):
        return self.client.calculate_cost(input_tokens, output_tokens)
    
    @property
    def provider(self):
        return self.client.provider
    
    @property
    def model(self):
        return self.client.model


def format_usage_line(usage_info: Dict) -> str:
    """Format usage info as ONE line summary."""
    return (
        f"[Usage] {usage_info['provider'].upper()}/{usage_info['model']} | "
        f"In: {usage_info['input_tokens']} | "
        f"Out: {usage_info['output_tokens']} | "
        f"Total: {usage_info['total_tokens']} | "
        f"Cost: ${usage_info['cost']:.4f}"
    )
