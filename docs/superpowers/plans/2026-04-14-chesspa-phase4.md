# ChessPA Phase 4: Dashboard API + Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the stats API endpoints and full frontend with navigation, dashboard (charts/stats), games list, game detail with chessboard, and settings page.

**Architecture:** Backend stats endpoints aggregate game data with SQL queries. Frontend uses Next.js App Router with react-chessboard for board visualization and recharts for charts. No rounded corners, dark/light theme via prefers-color-scheme.

**Tech Stack:** Next.js 15, TypeScript, react-chessboard, recharts, FastAPI, SQLAlchemy

---

## File Structure

```
backend/
├── app/api/
│   ├── stats.py               # Dashboard stats endpoints
│   └── router.py              # (modify: add stats router)
├── tests/
│   └── test_stats_api.py

frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # (modify: add nav)
│   │   ├── page.tsx            # Login (existing)
│   │   ├── coach/page.tsx      # (modify: show insights)
│   │   ├── dashboard/page.tsx  # Stats dashboard
│   │   ├── games/
│   │   │   ├── page.tsx        # Games list
│   │   │   └── [id]/page.tsx   # Game detail
│   │   └── settings/page.tsx   # Settings
│   ├── components/
│   │   ├── Nav.tsx             # Navigation bar
│   │   ├── ChessBoard.tsx      # Chessboard wrapper
│   │   └── EvalBar.tsx         # Evaluation bar
│   └── lib/
│       └── api.ts              # (existing)
```

---

### Task 1: Stats API Endpoints

**Files:**
- Create: `backend/app/api/stats.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_stats_api.py`

Endpoints:
- `GET /api/stats/overview` — current elo, winrate, total games, avg accuracy (query param: days=30)
- `GET /api/stats/openings` — winrate per opening (top 10)
- `GET /api/stats/elo-history` — elo datapoints for chart
- `GET /api/stats/phases` — avg phase scores across games
- `GET /api/stats/time-management` — placeholder (returns empty, needs clock data)

All require auth, filter by user_id, support optional `time_category` filter (bullet/blitz/rapid/classical).

---

### Task 2: Navigation Component

**Files:**
- Create: `frontend/src/components/Nav.tsx`
- Modify: `frontend/src/app/layout.tsx`

Nav shows: ChessPA logo, Coach, Dashboard, Games, Settings, username. Only shown when authenticated (check /auth/me). Login page has no nav.

---

### Task 3: Dashboard Page

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`

Shows: KPI tiles (elo, winrate, total games), elo history chart, winrate per opening bar chart, phase scores. Fetches from /api/stats/* endpoints. Uses recharts.

---

### Task 4: Games List Page

**Files:**
- Create: `frontend/src/app/games/page.tsx`

Shows: filterable list of games. Filters: platform, result, time category. Each row: opponent, opening, result (color coded), elo change, date. Click navigates to game detail.

---

### Task 5: Game Detail Page with Chessboard

**Files:**
- Create: `frontend/src/components/ChessBoard.tsx`
- Create: `frontend/src/components/EvalBar.tsx`
- Create: `frontend/src/app/games/[id]/page.tsx`

Split view: left = chessboard with move navigation, right = move list with annotations. If analysis exists, show eval bar and move classifications.

---

### Task 6: Settings Page

**Files:**
- Create: `frontend/src/app/settings/page.tsx`

Shows: connected accounts with auto-sync toggle, Chess.com username linking form, PGN upload. Calls existing API endpoints.

---

### Task 7: Coach Page Enhancement

**Files:**
- Modify: `frontend/src/app/coach/page.tsx`

For now: show user info + connected accounts + "sync games" button + game count. Coaching insights come in Phase 5.
