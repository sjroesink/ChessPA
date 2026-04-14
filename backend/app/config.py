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
    stockfish_depth: int = 20

    # LLM Provider
    llm_provider: str = "ollama"  # "ollama" or "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Move commentary
    llm_commentary_threshold: int = 25  # centipawn loss threshold; 25 = inaccuracy+, 100 = blunder only

    # vLLM (optional, local high-throughput LLM server)
    vllm_base_url: str = ""  # empty = disabled
    vllm_model: str = "qwen2.5-coder-32b-instruct-q4_k_m"

    # Lc0 / Maia (human-behaviour predictor per ELO bucket)
    lc0_path: str = "lc0"
    maia_weights_dir: str = "backend/engines/maia"
    maia_default_rating: int = 1500
    enable_maia: bool = True

    # Rich analysis
    enable_motifs: bool = True
    multipv_count: int = 3
    critical_moment_cp_gap: int = 150  # PV1 vs PV2 threshold (cp) for "only-move" flag

    # Opening book (Lichess CC0)
    opening_book_path: str = "backend/data/openings.tsv"

    model_config = {"env_prefix": "CHESSPA_", "env_file": ".env"}


settings = Settings()
