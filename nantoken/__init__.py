"""NanToken - Intelligent LLM Token Tracker"""

__version__ = "0.1.0"
__author__ = "NanToken Team"

# Core imports (always available)
from .core import SmartLLM
from .config import Config, load_config, create_default_config

# Optional imports - degrade gracefully if provider SDKs aren't installed
try:
    from .shell import SmartLLMShell
except ImportError:
    SmartLLMShell = None

try:
    from .runner import SmartLLMRunner
except ImportError:
    SmartLLMRunner = None

try:
    from .llm_client import LLMClient
except ImportError:
    LLMClient = None

try:
    from .universal_client import UniversalLLMClient
except ImportError:
    UniversalLLMClient = None

try:
    from .integrate import smart_ask, smart_estimate, smart_track, smart_plan
except ImportError:
    smart_ask = smart_estimate = smart_track = smart_plan = None

__all__ = [
    "SmartLLM",
    "SmartLLMShell",
    "SmartLLMRunner",
    "LLMClient",
    "UniversalLLMClient",
    "smart_ask",
    "smart_estimate",
    "smart_track",
    "smart_plan",
    "Config",
    "load_config",
    "create_default_config",
    "mcp_server",
]
