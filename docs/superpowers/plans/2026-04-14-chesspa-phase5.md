# ChessPA Phase 5: AI Coaching Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate AI coaching insights from aggregated game analysis data. Support both Claude API and Ollama as LLM backends via an abstraction layer. Expose coaching endpoints and update the coach page with real insights.

**Architecture:** LLM provider abstraction (`LLMProvider` protocol) with Claude and Ollama implementations. Coaching service aggregates game stats, builds a structured prompt, sends to configured LLM, parses structured JSON response into coaching insights. Celery task triggers periodically or on demand.

**Tech Stack:** anthropic SDK, httpx (Ollama API), Celery, pydantic

---

## File Structure

```
backend/
├── app/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py         # LLMProvider protocol + factory
│   │   ├── claude.py           # Claude API implementation
│   │   └── ollama.py           # Ollama implementation
│   ├── coaching/
│   │   ├── __init__.py
│   │   ├── prompts.py          # System + user prompt templates
│   │   ├── service.py          # Coaching insight generation logic
│   │   └── schemas.py          # Pydantic models for structured output
│   ├── api/
│   │   └── coaching.py         # Coaching API endpoints
│   ├── worker/
│   │   └── tasks.py            # (modify: add coaching task)
│   └── config.py               # (modify: add LLM settings)
├── tests/
│   ├── test_llm_provider.py
│   ├── test_coaching_service.py
│   └── test_coaching_api.py
```

---

### Task 1: LLM Provider Abstraction

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/provider.py`
- Create: `backend/app/llm/claude.py`
- Create: `backend/app/llm/ollama.py`
- Modify: `backend/app/config.py` (add LLM settings)
- Test: `backend/tests/test_llm_provider.py`

Config additions:
```python
# LLM Provider
llm_provider: str = "claude"  # "claude" or "ollama"
anthropic_api_key: str = ""
anthropic_model: str = "claude-sonnet-4-6"
ollama_base_url: str = "http://localhost:11434"
ollama_model: str = "llama3.1"
```

Provider protocol:
```python
from typing import Protocol

class LLMProvider(Protocol):
    async def generate(self, system: str, user: str) -> str: ...
```

Claude implementation uses anthropic SDK with prompt caching.
Ollama implementation uses httpx to POST to /api/generate.

Factory:
```python
def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    return ClaudeProvider(settings.anthropic_api_key, settings.anthropic_model)
```

---

### Task 2: Coaching Prompts + Schemas

**Files:**
- Create: `backend/app/coaching/__init__.py`
- Create: `backend/app/coaching/schemas.py`
- Create: `backend/app/coaching/prompts.py`

Schemas (pydantic):
```python
class CoachingInsightData(BaseModel):
    type: str  # weakness, pattern, strength
    title: str
    description: str
    severity: str  # high, medium, low
    related_game_indices: list[int]  # indices into the games list

class CoachingResponse(BaseModel):
    insights: list[CoachingInsightData]
```

Prompts: system prompt explaining the coach role + user prompt template that takes aggregated stats as input.

---

### Task 3: Coaching Service

**Files:**
- Create: `backend/app/coaching/service.py`
- Test: `backend/tests/test_coaching_service.py`

Service:
1. Fetch last N game summaries for user
2. Aggregate: opening stats, blunder distributions, phase scores
3. Build prompt with aggregated data + user elo
4. Send to LLM provider
5. Parse JSON response into CoachingInsightData list
6. Persist as CoachingInsight models
7. Expire old insights

---

### Task 4: Coaching API Endpoints

**Files:**
- Create: `backend/app/api/coaching.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_coaching_api.py`

Endpoints:
- GET /api/coaching/insights — active insights for user
- POST /api/coaching/refresh — regenerate insights now
- GET /api/coaching/insights/{id} — insight detail with related games

---

### Task 5: Coaching Celery Task

**Files:**
- Modify: `backend/app/worker/tasks.py`

Add generate_coaching task triggered every 6 hours or on demand.

---

### Task 6: Coach Page with Real Insights

**Files:**
- Modify: `frontend/src/app/coach/page.tsx`

Replace placeholder with real coaching insights from API. Show weakness/pattern/strength cards with severity colors and linked games.
