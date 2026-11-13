import os
from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
from pathlib import Path


MODEL_TIERS = {
    "gemini": {
        "id": os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash"),
        "label": "Gemini 2.5 Flash",
        "description": "Default - direct Gemini API",
        "provider": "gemini",
    },
    "minimax": {
        "id": os.getenv("MODEL_ID_MINIMAX", ""),
        "label": "MiniMax M2.5",
        "description": "Fast and cost-efficient",
        "provider": "zo",
    },
    "deepseek": {
        "id": os.getenv("MODEL_ID_DEEPSEEK", ""),
        "label": "DeepSeek R1 0528",
        "description": "Strong reasoning",
        "provider": "zo",
    },
    "qwen3": {
        "id": os.getenv("MODEL_ID_QWEN3", ""),
        "label": "Qwen3-235B-A22B",
        "description": "Highest quality - slower",
        "provider": "zo",
    },
}

DEFAULT_TIER = "gemini"
FALLBACK_ORDER = ["gemini", "minimax", "deepseek", "qwen3"]


class Settings(BaseSettings):
    zo_api_key: str = ""
    gemini_api_key: str = ""
    default_model: str = DEFAULT_TIER
    rate_limit_per_hour: int = 5
    daily_cap: int = 200
    max_html_bytes: int = 5 * 1024 * 1024

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def load_schema_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "schema_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_geo_rules_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "geo_rules_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
