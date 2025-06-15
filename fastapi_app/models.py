from typing import List, Dict

# Hardcoded list of available LLM models
AVAILABLE_MODELS: List[Dict[str, object]] = [
    {
        "name": "granite3.3:8b",
        "context_size": 131072,
        "description": "Granite 3.3 8B parameter model",
    },
    {
        "name": "granite3.2:8b",
        "context_size": 131072,
        "description": "Granite 3.2 8B parameter model",
    },
    {
        "name": "phi4:14b",
        "context_size": 16384,
        "description": "Phi-4 14B parameter model",
    },
    {
        "name": "llama3-chatqa:8b",
        "context_size": 8192,
        "description": "Llama 3 ChatQA 8B parameter model",
    },
    {
        "name": "qwen3:14b",
        "context_size": 40960,
        "description": "Qwen 3 14B parameter model",
    },
    {
        "name": "deepseek-r1:14b",
        "context_size": 131072,
        "description": "DeepSeek R1 14B parameter model",
    },
]

# Default model used for extraction
DEFAULT_MODEL: str = "granite3.3:8b"

# Derived helper constants
MODEL_CONTEXT_LIMITS = {m["name"]: m["context_size"] for m in AVAILABLE_MODELS}
MODEL_CONTEXT_LIMITS["default"] = 8000

MODEL_NAMES = [m["name"] for m in AVAILABLE_MODELS]
