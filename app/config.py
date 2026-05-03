from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    gemini_api_key: str = ""
    primary_llm: str = "gemini"
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_schema_config() -> dict:
    """Load schema configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "config" / "schema_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_geo_rules_config() -> dict:
    """Load GEO rules configuration from YAML file."""
    config_path = Path(__file__).parent.parent / "config" / "geo_rules_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

# Made with Bob
