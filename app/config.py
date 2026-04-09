from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

class Settings(BaseSettings):
    # --- SECRETS (No defaults - App must crash if missing) ---
    secret_key: str
    database_url: str
    
    # --- CONFIGURATION (Defaults are safe) ---
    algorithm: str = "HS256"  # Standard, safe default
    access_token_expire_minutes: int = 30  # Standard, safe default
    debug: bool = False  # Safe default (secure by default)
    
    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()

def configure_logging():
    """Configure structured logging for production"""
    import sys
    import logging
    
    # Set up standard logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use ConsoleRenderer for readable output in dev, JSONRenderer for prod
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )