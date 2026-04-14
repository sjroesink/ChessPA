from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chesspa:chesspa_dev@localhost:5432/chesspa"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-in-production"
    lichess_client_id: str = ""
    lichess_redirect_uri: str = "http://localhost:8000/auth/lichess/callback"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_url: str = "http://localhost:3000"
    encryption_key: str = ""

    # Stockfish
    stockfish_path: str = "stockfish"  # Path to Stockfish binary
    stockfish_threads: int = 16
    stockfish_hash_mb: int = 2048
    stockfish_depth: int = 24

    # LLM Provider
    llm_provider: str = "claude"  # "claude" or "ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Move commentary
    llm_commentary_mode: str = "single"  # "single" (per move, good for Ollama) or "batch" (one call, good for Claude)
    llm_commentary_threshold: int = 25  # centipawn loss threshold; 25 = inaccuracy+, 100 = blunder only

    model_config = {"env_prefix": "CHESSPA_", "env_file": ".env"}


settings = Settings()
