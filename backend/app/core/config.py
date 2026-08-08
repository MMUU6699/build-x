import os
import json
import logging
from pydantic_settings import BaseSettings
from functools import lru_cache

logger = logging.getLogger(__name__)


def _parse_extra_headers() -> dict | None:
    raw = os.environ.get("EXTRA_HEADERS")
    if not raw:
        return None
    try:
        headers = json.loads(raw)
        if isinstance(headers, dict):
            return headers
        logger.warning("EXTRA_HEADERS is not a JSON object, ignoring")
    except json.JSONDecodeError:
        logger.warning("EXTRA_HEADERS is not valid JSON, ignoring")
    return None


def _parse_extra_body() -> dict | None:
    raw = os.environ.get("EXTRA_BODY")
    if not raw:
        return None
    try:
        body = json.loads(raw)
        if isinstance(body, dict):
            return body
        logger.warning("EXTRA_BODY is not a JSON object, ignoring")
    except json.JSONDecodeError:
        logger.warning("EXTRA_BODY is not valid JSON, ignoring")
    return None


class Settings(BaseSettings):
    
    # Model provider configuration
    api_key: str | None = None
    api_base: str | None = None
    
    # Model configuration
    model_name: str = "gpt-4o"
    model_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: int = 2000

    # LLM gateway provider: "langchain" (default, supports many providers via
    # init_chat_model) or "openai" (direct OpenAI Python SDK, for
    # OpenAI / OpenAI-compatible endpoints).
    llm_provider: str = "langchain"
    
    # PostgreSQL configuration (Supabase Postgres-compatible)
    database_url: str = "postgresql+asyncpg://build_x:build_x@db:5432/build_x"

    # Supabase configuration
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_key: str | None = None
    supabase_jwt_secret: str | None = None  # JWT secret for local token verification
    supabase_storage_bucket: str = "files"
    
    # Frontend & CORS configuration
    frontend_url: str = "http://localhost:5173"

    # Daytona configuration
    daytona_api_key: str | None = None
    daytona_api_url: str | None = None
    
    # Sandbox configuration
    sandbox_address: str | None = None
    sandbox_image: str = "ghcr.io/mmuu6699/build-x-sandbox:latest"
    sandbox_name_prefix: str | None = None
    sandbox_ttl_minutes: int | None = 30
    sandbox_network: str | None = None  # Legacy: Docker network bridge name (unused with Daytona)
    sandbox_chrome_args: str | None = ""
    sandbox_https_proxy: str | None = None
    sandbox_http_proxy: str | None = None
    sandbox_no_proxy: str | None = None

    # Browser engine configuration
    browser_engine: str = "browser_use"  # "playwright" or "browser_use"
    
    # Search engine configuration
    search_provider: str | None = "bing_web"  # "baidu", "baidu_web", "google", "bing", "bing_web", "tavily", "serper", "custom"
    baidu_search_api_key: str | None = None
    bing_search_api_key: str | None = None
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None
    tavily_api_key: str | None = None
    # Serper.dev search configuration (SEARCH_PROVIDER=serper)
    serper_api_key: str | None = None
    # Custom search API configuration (SEARCH_PROVIDER=custom)
    search_api_url: str | None = None
    search_api_key: str | None = None
    search_api_key_header: str = "Authorization"
    search_api_key_header_prefix: str = "Bearer "
    search_api_key_param: str = ""
    search_api_method: str = "POST"
    search_query_field: str = "q"
    search_result_field: str = "results"
    search_title_field: str = "title"
    search_link_field: str = "link"
    search_snippet_field: str = "snippet"
    
    # Google Analytics configuration
    google_analytics_id: str | None = None

    # Auth configuration
    auth_provider: str = "none"  # "password", "none", "local"
    show_github_button: bool = True
    github_repository_url: str = "https://github.com/MMUU6699/build-x"
    password_salt: str | None = None
    password_hash_rounds: int = 10
    password_hash_algorithm: str = "pbkdf2_sha256"
    local_auth_email: str = "admin@example.com"
    local_auth_password: str = "admin"
    
    # Email configuration
    email_host: str | None = None  # "smtp.gmail.com"
    email_port: int | None = None  # 587
    email_username: str | None = None
    email_password: str | None = None
    email_from: str | None = None
    
    # JWT configuration (URL signing + optional login grace for legacy tokens)
    jwt_secret_key: str = "your-secret-key-here"  # Should be set in production
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Opaque auth sessions (browser Cookie + App Bearer), stored in Postgres
    session_cookie_name: str = "session_id"
    session_web_ttl_days: int = 14
    session_app_ttl_days: int = 30
    session_cookie_secure: bool = False  # set True behind HTTPS
    session_cookie_samesite: str = "lax"  # lax | strict | none
    # Accept legacy JWT access tokens during migration; new logins issue Redis sessions
    session_jwt_grace_enabled: bool = True
    
    # Extra headers and body for LLM requests (parsed from EXTRA_HEADERS / EXTRA_BODY env vars, JSON)
    extra_headers: dict | None = None
    extra_body: dict | None = None
    
    # Claw (OpenClaw) configuration
    claw_enabled: bool = False
    claw_image: str = "ghcr.io/mmuu6699/build-x-claw:latest"
    claw_name_prefix: str = "build-x-claw"
    claw_ttl_seconds: int = 3600
    claw_network: str | None = None  # Legacy: Docker network bridge name for claw containers (unused with Daytona)
    claw_ready_timeout: int = 300  # Max seconds to wait for claw container to become ready
    claw_address: str | None = None  # If set, use this fixed host instead of creating Docker containers
    claw_api_key: str | None = None  # Static API key accepted by the LLM proxy (for dev/fixed container)
    build_x_api_base_url: str = "http://backend:8000"  # URL of this backend accessible from claw containers

    # Task backend configuration: "local" (in-process asyncio, default)
    # or "celery" (distributed Celery workers; requires running `app.worker`)
    task_backend: str = "local"
    # Optional custom Celery broker URL, only used when TASK_BACKEND=celery.
    # Defaults to a Postgres-backed (SQLAlchemy transport) URL derived from
    # DATABASE_URL when unset. e.g. "db+postgresql://build_x:build_x@db:5432/build_x"
    celery_broker_url: str | None = None

    # MCP configuration
    mcp_config_path: str = "/etc/mcp.json"
    
    # Logging configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"
        extra = "ignore"
        
    def validate(self):
        """Validate configuration settings"""
        if not self.api_key:
            raise ValueError("API key is required")

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    settings = Settings()
    if not os.environ.get("OPENAI_API_KEY") and settings.api_key:
        os.environ["OPENAI_API_KEY"] = settings.api_key
    settings.extra_headers = _parse_extra_headers()
    settings.extra_body = _parse_extra_body()
    settings.validate()
    return settings 
