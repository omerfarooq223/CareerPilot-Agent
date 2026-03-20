# CLAUDE.md — CareerPilot Agent

This file is auto-read by Claude Code and AI assistants.
Read this fully before making any changes to the codebase.

---

## What this project is

CareerPilot is an autonomous AI agent that observes a developer's GitHub profile,
analyzes skill gaps against their target role, and takes actions to coach them
toward landing an internship. It runs a full agentic loop:
**Observe → Analyze → Remember → Plan → Act**

It also includes a FastAPI + HTML web UI for interacting with all skills manually.

---

## How to run
```bash
# Activate environment (Mac/Linux)
source venv/bin/activate

# Run the full autonomous agent (CLI)
python agent.py

# Run the web UI
uvicorn api.server:app --reload --port 8000
# Then open http://localhost:8000

# Run a single module
python -m skills.github_observer.github_observer
python -m skills.gap_analyzer.gap_analyzer
python -m skills.linkedin_writer.linkedin_writer
python -m memory.long_term
python -m planner.reasoner
python -m actions.executor

# Run tests
pytest tests/ -v
```

---

## Architecture
```
careerpilot/
├── agent.py                        # CoreAgent — boots the full CLI loop
├── CLAUDE.md                       # AI assistant briefing
├── AGENT.md                        # Agent architecture documentation
├── config/
│   ├── .env                        # Secrets — NEVER commit this
│   └── goals.yaml                  # Your target role, skills, companies
├── skills/
│   ├── registry.py                 # Plug-and-play skill registration
│   └── <skill_name>/               # One folder per skill
│       ├── <skill_name>.py         # Skill function
│       └── SKILL.md                # Skill contract
├── memory/
│   ├── short_term.py               # SessionMemory — current run state
│   └── long_term.py                # SQLite — snapshots, logs, LinkedIn history
│   └── latest_snapshot.json        # Committed snapshot — updated every agent.py run
├── planner/
│   └── reasoner.py                 # Groq-powered autonomous planner
├── actions/
│   ├── executor.py                 # Skill dispatcher + shared utilities
│   ├── error_handler.py            # Retry, timeout, fallback, rate limiting
│   └── security.py                 # Input sanitization, path guards
├── scripts/
│   └── weekly_reminder.py          # Reads latest_snapshot.json, sends HTML email
├── .github/
│   └── workflows/
│       └── weekly_reminder.yml     # Runs every Friday 6PM PKT via GitHub Actions
├── api/
│   ├── server.py                   # FastAPI server
│   └── routes/                     # dashboard, skills, agent endpoints
├── frontend/
│   └── index.html                  # Web UI (Arctic White theme)
├── output/                         # Generated files — gitignored
└── tests/                          # pytest unit + integration tests
```

---

## Architecture rules — follow these strictly

- **Never hardcode API keys** — always use `os.getenv()` + `config/.env`
- **Every new skill must be registered** in `actions/executor.py` using `registry.register()`
- **Every new skill must have its own folder** under `skills/` with a `SKILL.md`
- **All LLM calls go through Groq** — model is `llama-3.3-70b-versatile`
- **Gap analyzer uses `temperature=0.0`** — keeps scores consistent across runs
- **All data models use Pydantic** — no raw dicts passed between modules
- **All outputs are saved to `output/`** via `save_output()` in `executor.py`
- **All actions must call `session.remember_action()`** after execution
- **All actions must call `log_action()`** from `memory/long_term.py`
- **`load_dotenv()` uses absolute paths** via `Path(__file__).resolve()` — never relative
- **`executor.py` is a dispatcher only** — no skill logic lives there
- **Never overwrite previous audit files** — `audit_repo` saves to `audit_<repo>.md` and comparison to `audit_<repo>_comparison.md`
- **All core functions must have docstrings and return type annotations**
- **`memory/github_cache.json`** is auto-generated and gitignored — do not commit it

---

## Available skills

| Skill | Description | Output |
|---|---|---|
| `suggest_project` | Suggests a mini-project to fill the biggest skill gap | `output/suggested_project.md` |
| `audit_repo` | Smart audit — deep via MCP if available, metadata fallback | `output/audit_<repo>.md` |
| `rewrite_readme` | Rewrites a repo README professionally | `output/readme_<repo>.md` |
| `generate_dev_card` | Markdown developer profile card (use sparingly) | `output/developer_card.md` |
| `mock_interview_prep` | Role-specific interview questions | `output/mock_interview_prep.md` |
| `weekly_nudge` | Honest weekly progress report | `output/weekly_nudge.md` |
| `linkedin_writer` | HITL LinkedIn post generator with post memory | `output/linkedin_<type>_<repo>.md` |

---

## Web UI

The FastAPI server exposes the agent's skills as HTTP endpoints consumed by the frontend.
```bash
uvicorn api.server:app --reload --port 8000
```

Key endpoints:
- `GET  /api/dashboard`              — score, gaps, history
- `GET  /api/skills`                 — list all registered skills
- `POST /api/skills/{skill_name}`    — run a specific skill
- `POST /api/run`                    — full autonomous agent loop
- `GET  /api/repos`                  — list GitHub repos
- `GET  /api/history/memory`         — categorized memory (audits, projects, LinkedIn)
- `GET  /api/history/outputs/{file}` — get content of a specific output file
- `GET  /api/history/audits`         — action log from SQLite
- `GET  /api/history/linkedin`       — all LinkedIn posts from SQLite
- `GET /api/history/audits` — raw action log (developer use only, not exposed in UI)

---

## How to add a new skill

1. Create a folder: `skills/your_skill/`
2. Write the function in `skills/your_skill/your_skill.py`:
```python
def your_skill(session: SessionMemory) -> str:
    from actions.executor import call_groq, save_output
    logger.info("Action: your_skill")
    result = call_groq("your prompt here")
    save_output("your_skill_output.md", result)
    log_action("your_skill", "description")
    session.remember_action("your_skill")
    return result
```

3. Create `skills/your_skill/SKILL.md` using this template:
```markdown
# Skill: your_skill
## What it does
## Inputs
## Outputs
## When the planner should use this
## Dependencies
## Version
```

4. Register in `actions/executor.py`:
```python
from skills.your_skill.your_skill import your_skill
registry.register("your_skill", "Description")(your_skill)
```

5. Add a test in `tests/`

The planner will automatically consider it on the next run.

---

## Memory system

### Short-term (`memory/short_term.py`)
- Lives only for the current session
- Holds `GitHubProfile`, `GapReport`, list of actions taken
- Passed between all components as `session: SessionMemory`

### Long-term (`memory/long_term.py`)
- Persists in `memory/careerpilot.db` (SQLite)
- Tables:
  - `weekly_snapshots` — hirability score history week over week
  - `actions_log` — every action the agent has ever taken
  - `linkedin_posts` — every LinkedIn post with status, repo, and full content
  - `get_gap_trend()` — compares last two snapshots to show closed/new/persisted gaps

---

## Environment variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub Personal Access Token (read scope) |
| `GITHUB_USERNAME` | Your GitHub username |
| `GROQ_API_KEY` | Groq API key — free at console.groq.com |
| `REMINDER_EMAIL_SENDER` | Gmail address to send reminders from (stored as GitHub Secret) |
| `REMINDER_EMAIL_PASSWORD` | Gmail App Password (stored as GitHub Secret) |
| `REMINDER_EMAIL_RECEIVERS` | Comma-separated recipient emails (stored as GitHub Secret) |

---

## GitHub Actions

A weekly reminder workflow runs every Friday at 6PM PKT via GitHub Actions.
It reads `memory/latest_snapshot.json` (auto-generated by `agent.py`) and
sends an HTML email with your current score, gaps, and LinkedIn nudge.

- Workflow file: `.github/workflows/weekly_reminder.yml`
- Reminder script: `scripts/weekly_reminder.py`
- Snapshot file: `memory/latest_snapshot.json` — committed to repo, updated every `agent.py` run
- Secrets required: `REMINDER_EMAIL_SENDER`, `REMINDER_EMAIL_PASSWORD`, `REMINDER_EMAIL_RECEIVERS`
- To trigger manually: GitHub → Actions → Weekly CareerPilot Reminder → Run workflow

---

## Security measures

- Prompt injection detection on all inputs via `actions/security.py`
- Path traversal protection on all file writes
- Secret scrubbing before any LLM call
- Environment variable validation at boot via `check_env_vars()`
- Rate limiting on all Groq API calls via `RateLimiter`
- Repo name validation before any API or file operation

---

## What NOT to do

- Do not modify `agent.py` to hardcode actions — let the planner decide
- Do not add skill logic to `executor.py` — it is a dispatcher only
- Do not skip Pydantic models — raw dicts break type safety
- Do not commit `config/.env`, `output/`, or `memory/careerpilot.db`
- Do not use relative paths in `load_dotenv()` — always use `Path(__file__).resolve()`
- Do not add a skill without a `SKILL.md` file in its folder
- Do not change `temperature` in `gap_analyzer.py` — it must stay at `0.0` for score consistency