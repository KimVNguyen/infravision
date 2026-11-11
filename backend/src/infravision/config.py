"""Application configuration using Pydantic Settings."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres / Database
    database_url: str = Field(
        default="postgresql+psycopg://infravision:infravision@localhost:5435/infravision",
        description="Async SQLAlchemy database URL with psycopg driver",
    )

    # Procrastinate requires a standard libpq connection URI string
    @property
    def procrastinate_dsn(self) -> str:
        # Converts postgresql+psycopg:// into postgresql://
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")

    # LLM & Embeddings
    llm_provider: Literal["gemini", "openai", "anthropic", "mock"] = "mock"
    llm_api_key: str = ""
    embedding_model: str = "text-embedding-004"
    embedding_dim: int = 768

    # MCP Server
    mcp_server_name: str = "infravision-mcp"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000


settings = Settings()
