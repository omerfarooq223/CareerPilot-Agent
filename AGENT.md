# AGENT.md — CareerPilot Architecture

---

## Agent identity

**Name:** CareerPilot
**Type:** Autonomous goal-directed AI agent
**Purpose:** Coach a student developer toward landing their target internship
**LLM backbone:** Groq API — LLaMA 3.3 70B
**Memory:** SQLite (long-term) + in-memory Pydantic model (short-term)
**Interface:** CLI (`python agent.py`) + Web UI (`uvicorn api.server:app`)

---

## The agentic loop

Every run of `python agent.py` executes this loop once:
```
OBSERVE
  └── github_observer.py fetches full GitHub profile via REST API
      Output: GitHubProfile (Pydantic model)

ANALYZE
  └── gap_analyzer.py sends profile + goals.yaml to Groq (temperature=0.0)
      Output: GapReport (Pydantic model) with hirability score 1–10

REMEMBER
  └── long_term.py saves snapshot to SQLite
  └── get_score_history() retrieves week-over-week trend

PLAN
  └── reasoner.py sends gap report + history to Groq
      Groq decides: which skills to invoke, in what order, and why
      Output: AgentPlan (Pydantic model)

ACT
  └── executor.py dispatches each action through the skill registry
      Each action generates an output file in output/
      Each action logs itself to SQLite and session memory
```

---

## Data flow
```
goals.yaml ───────────────────────────────────────────────┐
                                                           ▼
GitHub API → GitHubProfile → GapReport → AgentPlan → Actions → output/
                                  │
                                  └──► SQLite (snapshots + action log + linkedin_posts)
```

---

## Web UI architecture
```
Browser → frontend/index.html (Arctic White theme)
               │
               ▼
         FastAPI (api/server.py)
               │
        ┌──────┼──────────┐
        ▼      ▼          ▼
  dashboard  skills     agent
  routes     routes     routes
        │      │          │
        └──────┴──────────┘
               │
        Same Python skills + memory
        as CLI agent
```

The web UI and CLI agent share all the same skill functions, memory, and planner — the API layer is purely a thin HTTP wrapper.

---

## Key data models

| Model | File | Description |
|---|---|---|
| `GitHubProfile` | `skills/github_observer/github_observer.py` | Full GitHub snapshot |
| `RepoSnapshot` | `skills/github_observer/github_observer.py` | Single repo data |
| `GapReport` | `skills/gap_analyzer/gap_analyzer.py` | Gap analysis result |
| `AgentPlan` | `planner/reasoner.py` | Planned actions for session |
| `SessionMemory` | `memory/short_term.py` | Current run state |

---

## Skill registry

Skills are registered in `actions/executor.py` using a decorator pattern:
```python
registry.register("skill_name", "description")(function)
```

The planner receives a list of available skill names and chooses which to invoke.
To disable a skill without deleting it:
```python
registry.disable("skill_name")
```

---

## Registered skills

| Skill | File | What it does |
|---|---|---|
| `suggest_project` | `skills/project_suggester/` | Suggests a mini-project for the biggest gap |
| `audit_repo` | Smart audit — MCP deep if available, metadata fallback. Compares with previous audit if one exists | `output/audit_<repo>.md` + `output/audit_<repo>_comparison.md` |
| `rewrite_readme` | `skills/readme_writer/` | Rewrites a repo README professionally |
| `generate_dev_card` | `skills/dev_card/` | Generates a markdown developer profile card |
| `mock_interview_prep` | `skills/interview_prep/` | Generates role-specific interview questions |
| `weekly_nudge` | `skills/nudge_writer/` | Writes an honest weekly progress report |
| `linkedin_writer` | `skills/linkedin_writer/` | LinkedIn post generator with Web UI HITL approval flow |

---

## Memory model

### Short-term (`memory/short_term.py`)
- Lives only for the current session
- Holds `GitHubProfile`, `GapReport`, and list of actions taken
- Passed between all components as `session: SessionMemory`

### Long-term (`memory/long_term.py`)
- Persists in `memory/careerpilot.db` (SQLite)
- **Engine**: Uses connection pooling via `database/db_utils.py` (default: 5 connections)
- Tables:
  - `weekly_snapshots` — hirability score history week over week
  - `actions_log` — every action the agent has ever taken
  - `linkedin_posts` — LinkedIn post history with repo, type, and approval status

---

## MCP integration (built into `audit_repo`)

The `audit_repo` skill automatically attempts to connect to the GitHub MCP
server via stdio when auditing a repo. If successful, it reads actual file
contents for a deep code review. If MCP is unavailable it silently falls back
to a metadata-based audit using the REST API data.

Requires: `npm install -g @modelcontextprotocol/server-github`

---

## Score consistency

The gap analyzer uses `temperature=0.0` and a fixed scoring rubric to ensure
consistent scores across runs. The rubric maps score ranges to specific profile
criteria so the LLM scores against objective standards, not subjective judgment.

---

## Security layer (`actions/security.py`)

- `check_env_vars()` — validates all required env vars at boot
- `check_prompt_injection()` — blocks injection attempts in inputs
- `safe_output_path()` — prevents path traversal on file writes
- `scrub_secrets()` — removes leaked keys before LLM calls
- `validate_repo_name()` — validates repo names before API calls
- `validate_goals()` — validates `goals.yaml` structure at boot

---

## Error handling layer (`actions/error_handler.py`)

- `CircuitBreaker` — handles external API failures (GitHub/Groq)
- `@retry` — retries failed functions with exponential backoff
- `@timeout` — cancels functions that exceed time limit
- `@fallback` — returns safe message instead of crashing agent
- `sanitize_input()` — strips null bytes and truncates long inputs
- `RateLimiter` — spaces out Groq API calls automatically

---

## Interactive Chat System (`POST /api/ask`)

The `/api/ask` endpoint provides conversational access to the agent via the web UI.

### Features

- **Conversation Memory** — Each chat session maintains history of recent messages
- **Real Data Answers** — Responses use actual GitHub profile data, not generic advice
- **Context Awareness** — Agent remembers previous questions when user asks follow-ups
- **Skill Triggering** — Users can request skills directly (e.g., "audit my repo")
- **Session Persistence** — Browser stores `session_id` in localStorage across page reloads

### How it works

1. User types a message in the chat bubble
2. Frontend sends: `{ message: "...", session_id: "..." }`
3. Backend receives message, loads conversation history for this session
4. Agent builds prompt with:
   - User's actual GitHub profile (repos, languages, score, gaps)
   - Last N messages from this conversation
   - List of available skills
5. Agent responds with intent: either `"qa"` (answer directly) or `"skill"` (trigger action)
6. Response stored in session history
7. Frontend displays response, maintaining context for next turn

### Example conversation flow

```
User: "How many Python repos do I have?"
Agent: "You have 6 repositories using Python."
       ↓ [stored in session history]

User: "What are their names?"
Agent: [recalls previous Python question]
       "The Python repositories are: autoresearch-agent, nexus-ai-pipeline, ..."
```

### Session Memory Storage

**Backend** (`api/routes/agent.py`):
- `_conversation_history` — in-memory dict: `session_id → [(role, content, timestamp), ...]`
- Max 5 recent messages included in prompt context
- Cleared on server restart (dev) or needs DB persistence (production)

**Frontend** (`frontend/index.html`):
- `chatSessionId` stored in `localStorage` under key `careerpilot_chat_session`
- Survives page reloads within same browser session
- New browser/private window = new session

### Testing

Run the main automated test suite:
```bash
pytest tests/ -v
```

---

## Extending the agent

### Add a new skill
See `CLAUDE.md → How to add a new skill`

### Add a new API endpoint
1. Add route function in appropriate `api/routes/*.py` file
2. Import and include router in `api/server.py` if new file
3. Add fetch call in `frontend/index.html`

### Add a new memory table
1. Add `CREATE TABLE` in `memory/long_term.py → init_db()`
2. Add save/retrieve functions following existing patterns

---

## Roadmap

- [x] GitHub observer (REST API)
- [x] Groq-powered gap analyzer (temperature=0.0, rubric-based scoring)
- [x] SQLite long-term memory
- [x] Autonomous planner
- [x] 7 action skills
- [x] Plug-and-play skill registry
- [x] GitHub MCP integration — built into audit_repo with automatic fallback
- [x] Error handling — retry, timeout, fallback, rate limiting
- [x] Security — prompt injection, path traversal, secret scrubbing
- [x] LinkedIn post generator with HITL approval and post memory
- [x] FastAPI web UI with Arctic White theme
- [x] Memory panel — past outputs, LinkedIn history, action log
- [x] Stop button for cancelling running tasks
- [x] Audit comparison — detects what improved between audits
- [x] Gap trend analysis — tracks which gaps closed/opened between sessions
- [x] goals.yaml auto-updater — syncs shipped_projects and skills from GitHub
- [x] GitHub Actions weekly email reminder
- [x] Railway deployment — live at https://web-production-e1faa.up.railway.app
- [x] GitHub data caching (1hr TTL, memory/github_cache.json)
- [x] User feedback loop — thumbs up/down per skill, feeds into planner
- [x] Outcome tracker — log applications with score correlation
- [x] Docstrings and return type annotations on core modules
- [ ] Persistent memory on Railway
- [ ] Docker containerization