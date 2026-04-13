# ChessPA — Design Specification

A personal chess coaching web application that analyzes games from Chess.com and Lichess, uses Stockfish for engine evaluation, and Claude API for pattern recognition and coaching insights.

## Overview

- **Goal:** Help chess players improve by identifying weaknesses, patterns, and strengths across their game history
- **UX approach:** Hybrid — coach-first landing with AI insights, full dashboard one click away
- **Target users:** Chess players of any level, starting with single-user, designed for multi-user from day one
- **Deployment:** Self-hosted on Unraid server

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (React), react-chessboard |
| Backend | Python, FastAPI |
| Task Queue | Celery + Redis |
| Database | PostgreSQL |
| Engine | Stockfish (via python-chess UCI) |
| AI Coaching | Claude API (Anthropic SDK) |
| Auth | Lichess OAuth2 PKCE + Chess.com username verification |

## Design Principles

- No rounded corners — sharp, clean aesthetic throughout
- Dark and light theme, defaulting to OS preference via `prefers-color-scheme`
- Minimal visual noise, focused on data clarity

## Pages

### 1. Login

Two login flows:

- **Lichess:** Full OAuth2 PKCE flow. User authorizes, we get token for API access.
- **Chess.com:** No OAuth available. User enters Chess.com username, we verify via public API (profile fetch). Games are fetched via public API (no auth needed).

First login creates user account. Lichess OAuth provides the session; Chess.com users authenticate via Lichess first, then link their Chess.com username.

### 2. Coach (Landing Page)

Primary view after login. Shows 3-5 AI-generated coaching insights:

- **Weakness** (red) — biggest area to improve, with linked games
- **Pattern** (amber) — recurring behavioral patterns (e.g., time trouble)
- **Strength** (teal) — what's working, keep doing it

Each insight links to related games. Refresh button triggers re-analysis.

### 3. Dashboard

Statistical overview with configurable time range:

- **KPI tiles:** Current Elo, winrate, total games, avg accuracy
- **Elo history graph:** Line chart over time
- **Winrate per opening:** Bar chart, top N openings
- **Blunders per game phase:** Opening / middlegame / endgame breakdown
- **Time management:** Average time per move by phase

### 4. Games List

Searchable, filterable list of all imported games:

- **Filters:** Platform, result, opening, date range, time control
- **Per row:** Opponent, opening name, result, Elo change, blunder count, date
- Click through to game detail

### 5. Game Detail

Split view:

- **Left:** Interactive chessboard with move navigation + evaluation bar
- **Right:** Move list with per-move annotations (Stockfish classification + eval delta), AI coach commentary on key moments

### 6. Settings

- Connected accounts with auto-sync toggle per platform
- PGN file upload for manual import
- User preferences (theme override, analysis depth, language)

## Data Model

### users

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| username | VARCHAR | Display name from first OAuth |
| created_at | TIMESTAMP | |
| last_login | TIMESTAMP | |
| preferences | JSONB | Theme, language, analysis depth |

### connected_accounts

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | → users.id |
| platform | VARCHAR | chess_com, lichess |
| platform_username | VARCHAR | |
| oauth_token_enc | BYTEA | Encrypted at rest |
| auto_sync | BOOLEAN | Default true |
| last_synced_at | TIMESTAMP | |

### games

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | → users.id |
| platform | VARCHAR | chess_com, lichess, pgn_upload |
| platform_game_id | VARCHAR | Nullable for uploads |
| pgn | TEXT | Full PGN |
| white_username | VARCHAR | |
| black_username | VARCHAR | |
| user_color | VARCHAR | white, black |
| result | VARCHAR | win, loss, draw |
| opening_name | VARCHAR | |
| opening_eco | VARCHAR | ECO code |
| time_control | VARCHAR | e.g., "600" for 10min |
| user_elo | INTEGER | |
| opponent_elo | INTEGER | |
| played_at | TIMESTAMP | |
| move_count | INTEGER | |
| import_source | VARCHAR | sync, pgn_upload |
| content_hash | VARCHAR UNIQUE | SHA256 for dedup |
| analysis_status | VARCHAR | pending, analyzing, done, failed |

**Indexes:** (user_id, played_at), (content_hash)

### move_analyses

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| game_id | UUID FK | → games.id |
| move_number | INTEGER | |
| color | VARCHAR | white, black |
| move_san | VARCHAR | e.g., "Nf3" |
| eval_before | FLOAT | Centipawns |
| eval_after | FLOAT | Centipawns |
| best_move_san | VARCHAR | |
| classification | VARCHAR | best, good, inaccuracy, mistake, blunder |
| time_spent_sec | INTEGER | Nullable, if available |

**Indexes:** (game_id)

### game_summaries

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| game_id | UUID FK UNIQUE | → games.id |
| blunders | INTEGER | |
| mistakes | INTEGER | |
| inaccuracies | INTEGER | |
| avg_eval_loss | FLOAT | |
| phase_scores | JSONB | {opening, middle, endgame} |
| time_trouble | BOOLEAN | |
| created_at | TIMESTAMP | |

### coaching_insights

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK | → users.id |
| type | VARCHAR | weakness, pattern, strength |
| title | VARCHAR | |
| description | TEXT | |
| severity | VARCHAR | high, medium, low |
| related_games | UUID[] | Array of game IDs |
| generated_at | TIMESTAMP | |
| expires_at | TIMESTAMP | Stale after new games analyzed |
| model_version | VARCHAR | Claude model used |

**Indexes:** (user_id, type)

## API Endpoints

### Auth

| Method | Path | Description |
|--------|------|-------------|
| GET | /auth/chess-com/login | Redirect to Chess.com OAuth |
| GET | /auth/chess-com/callback | Handle OAuth callback |
| GET | /auth/lichess/login | Redirect to Lichess OAuth |
| GET | /auth/lichess/callback | Handle OAuth callback |
| POST | /auth/logout | End session |
| GET | /auth/me | Current user + connected accounts |

### Games

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/games | List with filters (platform, result, opening, date, pagination) |
| GET | /api/games/:id | Game detail with moves |
| GET | /api/games/:id/analysis | Move analyses + game summary |
| POST | /api/games/import/pgn | Upload PGN file(s) |
| POST | /api/games/sync | Trigger manual sync |

### Dashboard Stats

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/stats/overview | Elo, winrate, totals (period param) |
| GET | /api/stats/openings | Winrate per opening |
| GET | /api/stats/phases | Performance per game phase |
| GET | /api/stats/time-management | Time usage patterns |
| GET | /api/stats/elo-history | Elo datapoints for chart |

### Coaching

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/coaching/insights | Active AI insights for user |
| POST | /api/coaching/refresh | Regenerate insights now |
| GET | /api/coaching/insights/:id | Insight detail + related games |

### Settings

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/settings | User preferences |
| PUT | /api/settings | Update preferences |
| POST | /api/accounts/connect | Link new platform account |
| DELETE | /api/accounts/:id | Unlink account |
| PUT | /api/accounts/:id/auto-sync | Toggle auto-sync |

## Analysis Pipeline

### Game Analysis (per game, on import)

1. Parse PGN via python-chess
2. For each move: run Stockfish eval at depth 20
3. Classify each move by centipawn loss:
   - best: Δ ≤ 10
   - good: Δ ≤ 25
   - inaccuracy: Δ ≤ 50
   - mistake: Δ ≤ 100
   - blunder: Δ > 100
4. Batch insert move_analyses
5. Compute game_summary (aggregate stats, phase detection)
6. Update game.analysis_status → "done"

Runs as Celery task, triggered on game save.

### Coaching Generation (batch, periodic)

Triggers: every 6 hours OR after 10+ newly analyzed games.

1. Fetch last 50 game_summaries for user
2. Aggregate: opening stats, blunder distributions, phase scores, time patterns
3. Send aggregated data to Claude API (not raw PGN — token efficient)
4. Structured JSON output: 3-5 insights with type, title, description, severity, related game IDs
5. Prompt includes player Elo for level-appropriate advice
6. System prompt cached, only data portion varies per call
7. Expire previous insights, store new ones

### Stockfish Configuration

- Depth: 20
- Threads: 2 (conservative for Unraid, configurable)
- Hash: 256 MB
- Runs as subprocess via python-chess UCI interface

## Import Pipeline

### Auto-sync

- Celery Beat schedule: every 30 minutes per connected account
- Fetches new games since last_synced_at from Chess.com / Lichess public APIs
- Deduplication via content_hash (SHA256 of moves + date + players)
- New games queued for Stockfish analysis

### PGN Upload

- Accepts .pgn files (single or multi-game)
- Parses and validates via python-chess
- Same dedup and analysis queue as auto-sync

## Deployment (Unraid)

- Docker Compose with services: next-frontend, fastapi-backend, celery-worker, celery-beat, redis, postgres
- Stockfish binary bundled in backend container
- Traefik reverse proxy for HTTPS
- PostgreSQL data on persistent Unraid share
