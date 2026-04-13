# ChessPA Phase 1: Project Setup + Backend Core + Auth

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold both frontend and backend projects, set up the database with all models, implement Lichess OAuth + Chess.com username linking, and expose core auth API endpoints.

**Architecture:** Monorepo with `frontend/` (Next.js) and `backend/` (FastAPI + SQLAlchemy + Alembic). PostgreSQL via Docker Compose for local dev. Session-based auth with HTTP-only cookies.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, asyncpg, Next.js 15, TypeScript, Docker Compose, PostgreSQL 16, Redis 7

**Spec:** `docs/superpowers/specs/2026-04-13-chesspa-design.md`

---

## File Structure

```
ChessPA/
├── docker-compose.yml              # Postgres + Redis for local dev
├── backend/
│   ├── pyproject.toml              # Python project config (uv)
│   ├── alembic.ini                 # Alembic config
│   ├── alembic/
│   │   ├── env.py                  # Alembic environment
│   │   └── versions/               # Migration files
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── database.py             # Async engine + session factory
│   │   ├── models/
│   │   │   ├── __init__.py         # Base + re-exports
│   │   │   ├── user.py             # User model
│   │   │   ├── connected_account.py # ConnectedAccount model
│   │   │   ├── game.py             # Game model
│   │   │   ├── move_analysis.py    # MoveAnalysis model
│   │   │   ├── game_summary.py     # GameSummary model
│   │   │   └── coaching_insight.py # CoachingInsight model
│   │   ├── auth/
│   │   │   ├── router.py           # Auth endpoints
│   │   │   ├── lichess.py          # Lichess OAuth PKCE client
│   │   │   ├── session.py          # Session management
│   │   │   └── dependencies.py     # get_current_user dependency
│   │   └── api/
│   │       ├── router.py           # API router aggregator
│   │       └── accounts.py         # Account linking endpoints
│   └── tests/
│       ├── conftest.py             # Fixtures: test DB, client, auth
│       ├── test_health.py          # Smoke test
│       ├── test_models.py          # Model creation tests
│       ├── test_auth.py            # Auth flow tests
│       └── test_accounts.py        # Account linking tests
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout with theme
│   │   │   ├── page.tsx            # Login page (landing when unauth)
│   │   │   ├── coach/page.tsx      # Coach landing (placeholder)
│   │   │   └── globals.css         # Base styles, theme, no border-radius
│   │   └── lib/
│   │       └── api.ts              # Backend API client
│   └── .env.local                  # NEXT_PUBLIC_API_URL
└── .gitignore
```

---

### Task 1: Project Scaffolding + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `frontend/package.json` (via create-next-app)

- [ ] **Step 1: Initialize git repo**

```bash
cd D:/Projects/ChessPA
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
.next/
frontend/.env.local

# IDE
.idea/
.vscode/

# Environment
.env
backend/.env

# Superpowers
.superpowers/
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: chesspa
      POSTGRES_PASSWORD: chesspa_dev
      POSTGRES_DB: chesspa
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 4: Start containers**

Run: `docker compose up -d`
Expected: Both postgres and redis containers running

- [ ] **Step 5: Create backend/pyproject.toml**

```toml
[project]
name = "chesspa-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.28.0",
    "cryptography>=44.0.0",
    "python-chess>=1.11.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 6: Install backend dependencies**

Run: `cd backend && uv sync --all-extras`
Expected: Virtual environment created, all deps installed

- [ ] **Step 7: Scaffold Next.js frontend**

Run: `cd D:/Projects/ChessPA && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --no-import-alias --use-npm`
Expected: Next.js project created in `frontend/`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: scaffold project with Docker Compose, FastAPI backend, Next.js frontend"
```

---

### Task 2: Backend Config + Database Connection

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Create backend/app/__init__.py**

```python
```

(Empty init file)

- [ ] **Step 2: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://chesspa:chesspa_dev@localhost:5432/chesspa"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-in-production"
    lichess_client_id: str = ""
    lichess_redirect_uri: str = "http://localhost:8000/auth/lichess/callback"
    frontend_url: str = "http://localhost:3000"
    encryption_key: str = ""  # Fernet key for token encryption

    model_config = {"env_prefix": "CHESSPA_", "env_file": ".env"}


settings = Settings()
```

- [ ] **Step 3: Create backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 4: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="ChessPA", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Write health check test**

Create `backend/tests/__init__.py` (empty) and `backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
```

Create `backend/tests/test_health.py`:

```python
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 6: Run test**

Run: `cd backend && uv run pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 7: Verify dev server starts**

Run: `cd backend && uv run uvicorn app.main:app --port 8000`
Expected: Server starts, `GET /health` returns `{"status": "ok"}`

- [ ] **Step 8: Commit**

```bash
git add backend/app/ backend/tests/
git commit -m "feat: FastAPI app with config, database connection, health endpoint"
```

---

### Task 3: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/connected_account.py`
- Create: `backend/app/models/game.py`
- Create: `backend/app/models/move_analysis.py`
- Create: `backend/app/models/game_summary.py`
- Create: `backend/app/models/coaching_insight.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Create backend/app/models/__init__.py**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.models.coaching_insight import CoachingInsight

__all__ = [
    "Base",
    "User",
    "ConnectedAccount",
    "Game",
    "MoveAnalysis",
    "GameSummary",
    "CoachingInsight",
]
```

- [ ] **Step 2: Create backend/app/models/user.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)

    connected_accounts = relationship("ConnectedAccount", back_populates="user")
    games = relationship("Game", back_populates="user")
    coaching_insights = relationship("CoachingInsight", back_populates="user")
```

- [ ] **Step 3: Create backend/app/models/connected_account.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(String(20))  # chess_com, lichess
    platform_username: Mapped[str] = mapped_column(String(100))
    oauth_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="connected_accounts")
```

- [ ] **Step 4: Create backend/app/models/game.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_user_played", "user_id", "played_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(String(20))
    platform_game_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pgn: Mapped[str] = mapped_column(Text)
    white_username: Mapped[str] = mapped_column(String(100))
    black_username: Mapped[str] = mapped_column(String(100))
    user_color: Mapped[str] = mapped_column(String(5))  # white, black
    result: Mapped[str] = mapped_column(String(4))  # win, loss, draw
    opening_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String(10), nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opponent_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    move_count: Mapped[int] = mapped_column(Integer, default=0)
    import_source: Mapped[str] = mapped_column(String(20))  # sync, pgn_upload
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    analysis_status: Mapped[str] = mapped_column(String(20), default="pending")

    user = relationship("User", back_populates="games")
    move_analyses = relationship("MoveAnalysis", back_populates="game", cascade="all, delete-orphan")
    summary = relationship("GameSummary", back_populates="game", uselist=False, cascade="all, delete-orphan")
```

- [ ] **Step 5: Create backend/app/models/move_analysis.py**

```python
import uuid

from sqlalchemy import String, Integer, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class MoveAnalysis(Base):
    __tablename__ = "move_analyses"
    __table_args__ = (
        Index("ix_move_analyses_game", "game_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    move_number: Mapped[int] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(5))
    move_san: Mapped[str] = mapped_column(String(10))
    eval_before: Mapped[float] = mapped_column(Float)
    eval_after: Mapped[float] = mapped_column(Float)
    best_move_san: Mapped[str] = mapped_column(String(10))
    classification: Mapped[str] = mapped_column(String(15))  # best, good, inaccuracy, mistake, blunder
    time_spent_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    game = relationship("Game", back_populates="move_analyses")
```

- [ ] **Step 6: Create backend/app/models/game_summary.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class GameSummary(Base):
    __tablename__ = "game_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"), unique=True)
    blunders: Mapped[int] = mapped_column(Integer, default=0)
    mistakes: Mapped[int] = mapped_column(Integer, default=0)
    inaccuracies: Mapped[int] = mapped_column(Integer, default=0)
    avg_eval_loss: Mapped[float] = mapped_column(Float, default=0.0)
    phase_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    time_trouble: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    game = relationship("Game", back_populates="summary")
```

- [ ] **Step 7: Create backend/app/models/coaching_insight.py**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class CoachingInsight(Base):
    __tablename__ = "coaching_insights"
    __table_args__ = (
        Index("ix_coaching_insights_user_type", "user_id", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(20))  # weakness, pattern, strength
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10))  # high, medium, low
    related_games: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_version: Mapped[str] = mapped_column(String(50))

    user = relationship("User", back_populates="coaching_insights")
```

- [ ] **Step 8: Write model tests**

Create `backend/tests/test_models.py`:

```python
import uuid

from app.models import User, ConnectedAccount, Game, MoveAnalysis, GameSummary, CoachingInsight


def test_user_creation():
    user = User(username="testplayer")
    assert user.username == "testplayer"
    assert user.preferences == {}


def test_connected_account_creation():
    user_id = uuid.uuid4()
    account = ConnectedAccount(
        user_id=user_id,
        platform="lichess",
        platform_username="testplayer",
        auto_sync=True,
    )
    assert account.platform == "lichess"
    assert account.auto_sync is True


def test_game_creation():
    from datetime import datetime, timezone

    game = Game(
        user_id=uuid.uuid4(),
        platform="chess_com",
        pgn="1. e4 e5 *",
        white_username="player1",
        black_username="player2",
        user_color="white",
        result="win",
        played_at=datetime.now(timezone.utc),
        import_source="sync",
        content_hash="abc123",
    )
    assert game.analysis_status == "pending"
    assert game.result == "win"


def test_move_analysis_creation():
    analysis = MoveAnalysis(
        game_id=uuid.uuid4(),
        move_number=14,
        color="white",
        move_san="Bxf7+",
        eval_before=0.5,
        eval_after=-2.7,
        best_move_san="O-O",
        classification="blunder",
    )
    assert analysis.classification == "blunder"
    assert analysis.eval_after == -2.7


def test_game_summary_creation():
    summary = GameSummary(
        game_id=uuid.uuid4(),
        blunders=2,
        mistakes=3,
        inaccuracies=5,
        avg_eval_loss=0.45,
        phase_scores={"opening": 92, "middle": 71, "endgame": 65},
        time_trouble=True,
    )
    assert summary.blunders == 2
    assert summary.phase_scores["middle"] == 71


def test_coaching_insight_creation():
    insight = CoachingInsight(
        user_id=uuid.uuid4(),
        type="weakness",
        title="Queen endgame struggles",
        description="You lose material in queen endgames frequently.",
        severity="high",
        related_games=[uuid.uuid4(), uuid.uuid4()],
        model_version="claude-sonnet-4-6",
    )
    assert insight.type == "weakness"
    assert len(insight.related_games) == 2
```

- [ ] **Step 9: Run model tests**

Run: `cd backend && uv run pytest tests/test_models.py -v`
Expected: All 6 tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: add all SQLAlchemy models — users, accounts, games, analyses, coaching"
```

---

### Task 4: Alembic Setup + Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (auto-generated migration)

- [ ] **Step 1: Initialize alembic**

```bash
cd backend && uv run alembic init alembic
```

- [ ] **Step 2: Edit backend/alembic.ini**

Set the sqlalchemy.url line:

```ini
sqlalchemy.url = postgresql+asyncpg://chesspa:chesspa_dev@localhost:5432/chesspa
```

- [ ] **Step 3: Edit backend/alembic/env.py**

Replace the entire file:

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "initial schema"`
Expected: Migration file created in `alembic/versions/`

- [ ] **Step 5: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: All tables created in PostgreSQL

- [ ] **Step 6: Verify tables exist**

Run: `docker exec -it chesspa-postgres-1 psql -U chesspa -c "\dt"`
Expected: Tables listed: users, connected_accounts, games, move_analyses, game_summaries, coaching_insights

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic with initial migration for all tables"
```

---

### Task 5: Lichess OAuth PKCE + Session Management

**Files:**
- Create: `backend/app/auth/__init__.py`
- Create: `backend/app/auth/lichess.py`
- Create: `backend/app/auth/session.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/router.py`
- Modify: `backend/app/main.py` (register auth router)
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Create backend/app/auth/__init__.py**

```python
```

- [ ] **Step 2: Create backend/app/auth/session.py**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

SESSION_COOKIE = "chesspa_session"


async def get_or_create_user(db: AsyncSession, lichess_username: str) -> User:
    result = await db.execute(
        select(User).where(User.username == lichess_username)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=lichess_username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(last_login=datetime.now(timezone.utc))
        )
        await db.commit()
    return user
```

- [ ] **Step 3: Create backend/app/auth/lichess.py**

```python
import hashlib
import secrets
import base64

import httpx

from app.config import settings

LICHESS_AUTH_URL = "https://lichess.org/oauth"
LICHESS_TOKEN_URL = "https://lichess.org/api/token"
LICHESS_ACCOUNT_URL = "https://lichess.org/api/account"


def generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def get_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.lichess_client_id,
        "redirect_uri": settings.lichess_redirect_uri,
        "scope": "",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{LICHESS_AUTH_URL}?{query}"


async def exchange_code(code: str, code_verifier: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LICHESS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.lichess_redirect_uri,
                "client_id": settings.lichess_client_id,
                "code_verifier": code_verifier,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_lichess_user(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            LICHESS_ACCOUNT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 4: Create backend/app/auth/dependencies.py**

```python
import uuid

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.session import SESSION_COOKIE

# In-memory session store — replace with Redis in production
_sessions: dict[str, uuid.UUID] = {}


def set_session(session_id: str, user_id: uuid.UUID) -> None:
    _sessions[session_id] = user_id


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


async def get_current_user(
    chesspa_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if chesspa_session is None or chesspa_session not in _sessions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user_id = _sessions[chesspa_session]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

- [ ] **Step 5: Create backend/app/auth/router.py**

```python
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.lichess import generate_pkce, get_authorize_url, exchange_code, get_lichess_user
from app.auth.session import get_or_create_user, SESSION_COOKIE
from app.auth.dependencies import get_current_user, set_session, clear_session

router = APIRouter(prefix="/auth", tags=["auth"])

# Temporary state store — maps state to code_verifier
_oauth_states: dict[str, str] = {}


@router.get("/lichess/login")
async def lichess_login():
    state = secrets.token_urlsafe(32)
    verifier, challenge = generate_pkce()
    _oauth_states[state] = verifier
    url = get_authorize_url(state, challenge)
    return RedirectResponse(url)


@router.get("/lichess/callback")
async def lichess_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    verifier = _oauth_states.pop(state, None)
    if verifier is None:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    token = await exchange_code(code, verifier)
    lichess_data = await get_lichess_user(token)
    username = lichess_data["username"]

    user = await get_or_create_user(db, username)

    # Upsert connected account for Lichess
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.platform == "lichess",
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        account = ConnectedAccount(
            user_id=user.id,
            platform="lichess",
            platform_username=username,
        )
        db.add(account)
        await db.commit()

    session_id = secrets.token_urlsafe(32)
    set_session(session_id, user.id)

    response = RedirectResponse(settings.frontend_url)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return response


@router.post("/logout")
async def logout(
    response: Response,
    chesspa_session: str | None = None,
):
    if chesspa_session:
        clear_session(chesspa_session)
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/me")
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.connected_accounts))
    )
    user = result.scalar_one()
    return {
        "id": str(user.id),
        "username": user.username,
        "connected_accounts": [
            {
                "id": str(a.id),
                "platform": a.platform,
                "platform_username": a.platform_username,
                "auto_sync": a.auto_sync,
            }
            for a in user.connected_accounts
        ],
    }
```

- [ ] **Step 6: Register auth router in main.py**

Replace `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router


def create_app() -> FastAPI:
    app = FastAPI(title="ChessPA", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth_router)

    return app


app = create_app()
```

- [ ] **Step 7: Write auth tests**

Create `backend/tests/test_auth.py`:

```python
from unittest.mock import AsyncMock, patch

from app.auth.dependencies import set_session


async def test_me_unauthenticated(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_authenticated(client, app):
    """Test /auth/me with a valid session."""
    from app.database import get_db
    from app.models.user import User
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from app.models import Base
    from app.config import settings
    import uuid

    # Use real test DB
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Create test user
    async with session_factory() as db:
        user = User(username="testplayer")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    session_id = "test-session-123"
    set_session(session_id, user_id)

    response = await client.get(
        "/auth/me",
        cookies={"chesspa_session": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testplayer"
    assert data["id"] == str(user_id)

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_lichess_login_redirects(client):
    """Test that /auth/lichess/login returns a redirect to Lichess."""
    response = await client.get("/auth/lichess/login", follow_redirects=False)
    assert response.status_code == 307
    assert "lichess.org/oauth" in response.headers["location"]


async def test_logout(client):
    response = await client.post("/auth/logout")
    assert response.status_code == 200
```

- [ ] **Step 8: Run auth tests**

Run: `cd backend && uv run pytest tests/test_auth.py -v`
Expected: All 4 tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/auth/ backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: Lichess OAuth PKCE login, session management, /auth/me endpoint"
```

---

### Task 6: Chess.com Username Linking

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/api/accounts.py`
- Modify: `backend/app/main.py` (register API router)
- Test: `backend/tests/test_accounts.py`

- [ ] **Step 1: Create backend/app/api/__init__.py**

```python
```

- [ ] **Step 2: Create backend/app/api/accounts.py**

```python
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

CHESS_COM_PROFILE_URL = "https://api.chess.com/pub/player/{username}"


class ConnectChessComRequest(BaseModel):
    username: str


@router.post("/connect/chess-com")
async def connect_chess_com(
    body: ConnectChessComRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify username exists on Chess.com
    async with httpx.AsyncClient() as client:
        response = await client.get(
            CHESS_COM_PROFILE_URL.format(username=body.username.lower()),
            headers={"User-Agent": "ChessPA/0.1"},
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Chess.com user not found")
        response.raise_for_status()

    # Check if already linked
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.platform == "chess_com",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.platform_username = body.username.lower()
        await db.commit()
    else:
        account = ConnectedAccount(
            user_id=user.id,
            platform="chess_com",
            platform_username=body.username.lower(),
        )
        db.add(account)
        await db.commit()

    return {"status": "connected", "platform": "chess_com", "username": body.username.lower()}


@router.delete("/{account_id}")
async def disconnect_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == uuid.UUID(account_id),
            ConnectedAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    # Don't allow disconnecting last Lichess account (needed for auth)
    if account.platform == "lichess":
        raise HTTPException(status_code=400, detail="Cannot disconnect Lichess account (used for login)")

    await db.delete(account)
    await db.commit()
    return {"status": "disconnected"}


@router.put("/{account_id}/auto-sync")
async def toggle_auto_sync(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == uuid.UUID(account_id),
            ConnectedAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    account.auto_sync = not account.auto_sync
    await db.commit()
    return {"auto_sync": account.auto_sync}
```

- [ ] **Step 3: Create backend/app/api/router.py**

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router

router = APIRouter()
router.include_router(accounts_router)
```

- [ ] **Step 4: Register API router in main.py**

Replace `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.auth.router import router as auth_router
from app.api.router import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="ChessPA", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(api_router)

    return app


app = create_app()
```

- [ ] **Step 5: Write accounts tests**

Create `backend/tests/test_accounts.py`:

```python
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.auth.dependencies import set_session, get_current_user


async def _setup_db(app):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override
    return engine, factory


async def _create_user(factory, username="testplayer"):
    async with factory() as db:
        user = User(username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_connect_chess_com(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)
    set_session("s1", user.id)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("app.api.accounts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        response = await client.post(
            "/api/accounts/connect/chess-com",
            json={"username": "TestPlayer"},
            cookies={"chesspa_session": "s1"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "chess_com"
    assert data["username"] == "testplayer"

    await _cleanup(engine, app)


async def test_connect_chess_com_not_found(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)
    set_session("s2", user.id)

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("app.api.accounts.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        response = await client.post(
            "/api/accounts/connect/chess-com",
            json={"username": "nonexistent"},
            cookies={"chesspa_session": "s2"},
        )

    assert response.status_code == 404

    await _cleanup(engine, app)


async def test_toggle_auto_sync(client, app):
    engine, factory = await _setup_db(app)
    user = await _create_user(factory)

    async with factory() as db:
        account = ConnectedAccount(
            user_id=user.id,
            platform="chess_com",
            platform_username="testplayer",
            auto_sync=True,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        account_id = str(account.id)

    set_session("s3", user.id)

    response = await client.put(
        f"/api/accounts/{account_id}/auto-sync",
        cookies={"chesspa_session": "s3"},
    )
    assert response.status_code == 200
    assert response.json()["auto_sync"] is False

    await _cleanup(engine, app)
```

- [ ] **Step 6: Run accounts tests**

Run: `cd backend && uv run pytest tests/test_accounts.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS (health + models + auth + accounts)

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/tests/test_accounts.py
git commit -m "feat: Chess.com username linking, account disconnect, auto-sync toggle"
```

---

### Task 7: Frontend Shell + Theme + Login Page

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/app/coach/page.tsx`

- [ ] **Step 1: Create frontend/src/lib/api.ts**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, options?: RequestInit) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    ...options,
  });
  return response;
}

export async function apiJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Replace frontend/src/app/globals.css**

```css
:root {
  --bg: #ffffff;
  --bg-secondary: #f5f5f5;
  --fg: #111111;
  --fg-secondary: #666666;
  --border: #e0e0e0;
  --accent: #111111;
  --danger: #dc2626;
  --warning: #d97706;
  --success: #059669;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0a0a0a;
    --bg-secondary: #141414;
    --fg: #eeeeee;
    --fg-secondary: #999999;
    --border: #2a2a2a;
    --accent: #eeeeee;
    --danger: #ef4444;
    --warning: #f59e0b;
    --success: #10b981;
  }
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: var(--bg);
  color: var(--fg);
  font-family: system-ui, -apple-system, sans-serif;
  line-height: 1.5;
}

a {
  color: var(--accent);
  text-decoration: none;
}

button {
  background: var(--accent);
  color: var(--bg);
  border: 1px solid var(--border);
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  border-radius: 0;
  font-family: inherit;
}

button:hover {
  opacity: 0.85;
}
```

- [ ] **Step 3: Replace frontend/src/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChessPA",
  description: "Your personal chess coach",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Replace frontend/src/app/page.tsx (Login page)**

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: "16px",
      }}
    >
      <div style={{ fontSize: "48px" }}>&#9823;</div>
      <h1 style={{ fontSize: "32px", fontWeight: 600 }}>ChessPA</h1>
      <p style={{ color: "var(--fg-secondary)", marginBottom: "24px" }}>
        Je persoonlijke schaakcoach
      </p>
      <a href={`${API_URL}/auth/lichess/login`}>
        <button style={{ width: "260px", marginBottom: "8px" }}>
          Login met Lichess
        </button>
      </a>
    </main>
  );
}
```

- [ ] **Step 5: Create frontend/src/app/coach/page.tsx (placeholder)**

```tsx
export default function CoachPage() {
  return (
    <main style={{ padding: "32px" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 600, marginBottom: "16px" }}>
        Coach
      </h1>
      <p style={{ color: "var(--fg-secondary)" }}>
        Analyse wordt geladen...
      </p>
    </main>
  );
}
```

- [ ] **Step 6: Create frontend/.env.local**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 7: Verify frontend starts**

Run: `cd frontend && npm run dev`
Expected: Next.js dev server on localhost:3000, login page renders with dark/light theme

- [ ] **Step 8: Commit**

```bash
git add frontend/src/ frontend/.env.local
git commit -m "feat: frontend shell with login page, dark/light theme, API client"
```

---

### Task 8: Full Integration Smoke Test

- [ ] **Step 1: Ensure Docker Compose running**

Run: `docker compose up -d`

- [ ] **Step 2: Run migrations**

Run: `cd backend && uv run alembic upgrade head`

- [ ] **Step 3: Start backend**

Run: `cd backend && uv run uvicorn app.main:app --reload --port 8000`

- [ ] **Step 4: Start frontend**

Run: `cd frontend && npm run dev`

- [ ] **Step 5: Verify endpoints**

- `GET http://localhost:8000/health` → `{"status": "ok"}`
- `GET http://localhost:8000/auth/me` → 401
- `GET http://localhost:8000/auth/lichess/login` → redirects to lichess.org
- `http://localhost:3000` → Login page renders

- [ ] **Step 6: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: phase 1 complete — backend core, auth, models, frontend shell"
```

---

## Remaining Phases (to be detailed)

### Phase 2: Game Import Pipeline
- Chess.com API client (fetch games by month)
- Lichess API client (stream games by user)
- PGN parser + metadata extraction
- Dedup via content_hash
- Celery setup + Redis broker
- Auto-sync Celery Beat task
- PGN upload endpoint
- `/api/games` list endpoint with filters

### Phase 3: Stockfish Analysis Pipeline
- Stockfish UCI integration via python-chess
- Move-by-move analysis Celery task
- Classification by centipawn loss thresholds
- Game summary computation (phase detection, time trouble)
- Analysis status tracking
- `/api/games/:id/analysis` endpoint

### Phase 4: Dashboard API + Frontend
- Stats aggregation endpoints (overview, openings, phases, time, elo history)
- Dashboard page with charts (recharts or similar)
- Games list page with filters
- Game detail page with react-chessboard + eval bar
- Navigation component

### Phase 5: Claude Coaching Layer
- Coaching prompt design with structured output
- Batch insight generation Celery task
- Insight refresh logic (expire + regenerate)
- Coach landing page with insights
- `/api/coaching/*` endpoints

### Phase 6: Deployment
- Multi-stage Dockerfiles (frontend + backend)
- Production docker-compose.yml
- Traefik labels for HTTPS
- Environment variable configuration
- Stockfish binary in backend container
