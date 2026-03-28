# 🤖 CareerPilot

A fully autonomous AI agent that watches your GitHub, analyzes your skill gaps,
and coaches you toward landing your target internship — week over week.

Built with a real agentic loop: **Observe → Analyze → Remember → Plan → Act**

---

## How it works
```
python agent.py
      │
      ├── OBSERVE   → Reads your entire GitHub profile via REST API
      ├── ANALYZE   → Groq LLM compares you vs your target role (consistent scoring)
      ├── REMEMBER  → Saves progress snapshots to SQLite (week-over-week tracking)
      ├── PLAN      → Agent autonomously decides what to do next
      └── ACT       → Executes skills via registry, saves outputs to output/
```

---

## Quickstart
```bash
git clone https://github.com/omerfarooq223/CareerPilot-Agent
cd CareerPilot-Agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env   # fill in your keys
```

**Run the CLI agent:**
```bash
python agent.py
```

**Run the web UI:**
```bash
uvicorn api.server:app --reload --port 8000
# Open http://localhost:8000
```
**Or visit the live demo:** https://web-production-e1faa.up.railway.app

---

## Configuration

### `config/config.py`
Centralized configuration loader. Uses `config/.env` for secrets and defines app-wide constants.

### `config/goals.yaml`
```yaml
model_provider: "groq"
model_name: "llama-3.3-70b-versatile"
target_role: "AI/ML Intern"
target_timeline: "3 months"
target_companies:
  - "Arbisoft"
  - "Folio3"
preferred_stack:
  - "FastAPI"
  - "Django"
```

---

## Skills

| Skill | Description | Output |
|---|---|---|
| `suggest_project` | Tailored mini-project to fill your biggest skill gap | `output/suggested_project.md` |
| `audit_repo` | Smart audit — deep code via MCP if available, metadata fallback | `output/audit_<repo>.md` |
| `rewrite_readme` | Professional README rewrite | `output/readme_<repo>.md` |
| `generate_dev_card` | Markdown developer profile card | `output/developer_card.md` |
| `mock_interview_prep` | Role-specific interview questions | `output/mock_interview_prep.md` |
| `weekly_nudge` | Honest weekly progress report | `output/weekly_nudge.md` |
| `linkedin_writer` | HITL LinkedIn post generator with post memory | `output/linkedin_<type>_<repo>.md` |
| `update_goals` | Auto-syncs shipped_projects and skills from GitHub | `config/goals.yaml` |

---

## Project structure
```
CareerPilot-Agent/
├── agent.py                  # Main entrypoint: runs the agentic loop
├── AGENT.md                  # Agent architecture documentation
├── CLAUDE.md                 # AI assistant briefing and rules
├── LICENSE                   # Project license
├── Procfile                  # Railway deployment start command
├── README.md                 # Project documentation (this file)
├── pyproject.toml            # Python packaging and build config
├── railway.json              # Railway deployment config
├── requirements.txt          # Python dependencies
├── .gitignore                # Files/folders to exclude from git
├── actions/                  # Action dispatcher and security
│   ├── error_handler.py      # Retry, timeout, fallback, rate limiting
│   ├── executor.py           # Skill dispatcher, output saving
│   └── security.py           # Input sanitization, path guards
├── api/                      # FastAPI backend and API routes
│   ├── server.py             # FastAPI app entrypoint
│   └── routes/               # API endpoints
│       ├── __init__.py
│       ├── agent.py          # POST /api/run — full agentic loop
│       ├── dashboard.py      # GET /api/dashboard, history endpoints
│       ├── skills.py         # POST /api/skills/{skill_name}
├── config/                   # Configuration and secrets
│   ├── .env                  # Environment variables (never committed)
│   ├── config.py             # Centralized config loader
│   └── goals.yaml            # Target role, skills, companies
├── credentials/              # Gmail API credentials (gitignored)
│   ├── credentials.json      # OAuth2 client secrets
│   └── token.json            # OAuth2 user token
├── database/                 # Database utilities
│   └── db_utils.py           # SQLite connection pooling
├── frontend/                 # Web UI
│   └── index.html            # Single-page HTML UI
├── memory/                   # Agent memory (SQLite, snapshots, cache)
│   ├── __pycache__/
│   ├── careerpilot.db        # SQLite DB (gitignored)
│   ├── github_cache.json     # GitHub API cache (gitignored)
│   ├── latest_snapshot.json  # Last committed agent state
│   ├── long_term.py          # Long-term memory logic
│   └── short_term.py         # Short-term/session memory logic
├── planner/                  # Autonomous planner
│   └── reasoner.py           # Groq-powered planning logic
├── scripts/                  # Automation and email scripts
│   ├── careerpilot_daemon.py # Local daemon for weekly email
│   ├── send_gmail_api.py     # Sends email via Gmail API
│   └── weekly_reminder.py    # Email content builder
├── skills/                   
│   ├── registry.py           # Skill registration system
│   ├── audit_repo/           # Repo audit skill
│   │   ├── SKILL.md
│   │   └── audit_repo.py
│   ├── dev_card/             # Developer card skill
│   │   ├── SKILL.md
│   │   └── dev_card.py
│   ├── gap_analyzer/         # Gap analysis skill
│   │   ├── SKILL.md
│   │   └── gap_analyzer.py
│   ├── github_observer/      # GitHub profile observer
│   │   ├── SKILL.md
│   │   └── github_observer.py
│   ├── goals_updater/        # Goals updater skill
│   │   ├── SKILL.md
│   │   └── goals_updater.py
│   ├── interview_prep/       # Interview prep skill
│   │   ├── SKILL.md
│   │   └── interview_prep.py
│   ├── linkedin_writer/      # LinkedIn post generator
│   │   ├── SKILL.md
│   │   └── linkedin_writer.py
│   ├── nudge_writer/         # Weekly nudge skill
│   │   ├── SKILL.md
│   │   └── nudge_writer.py
│   ├── project_suggester/    # Project suggestion skill
│   │   ├── SKILL.md
│   │   └── project_suggester.py
│   ├── readme_writer/        # README rewrite skill
│   │   ├── SKILL.md
│   │   └── readme_writer.py
├── tests/                    # Unit and integration tests
│   ├── test_memory.py
│   ├── test_observer.py
│   └── test_planner.py
└── venv/                     # Python virtual environment (gitignored)
```
````

## Stack

| Component | Technology |
|---|---|
| **LLM** | Groq API — LLaMA 3.3 70B |
| **GitHub data** | GitHub REST API + GitHub MCP (optional deep audits) |
| **Memory** | SQLite |
| **Data models** | Pydantic |
| **Web framework** | FastAPI |
| **Frontend** | Vanilla HTML/CSS/JS + marked.js |
| **CLI** | Rich + Loguru |
| **Error handling** | Circuit breaker + custom retry/timeout/fallback |
| **Security** | Prompt injection guard, path traversal protection |
| **Testing** | pytest |
| **Scheduling** | Local cron job (weekly reminder) |
| **Deployment** | Railway (free tier) |
| **Caching** | Local JSON (1hr GitHub cache) |
| **Connection Pooling**| SQLite pooling (5 connections) |

---

## Adding a new skill

1. Create `skills/your_skill/your_skill.py`
2. Create `skills/your_skill/SKILL.md`
3. Register in `actions/executor.py`:
```python
from skills.your_skill.your_skill import your_skill
registry.register("your_skill", "Description")(your_skill)
```

The planner and web UI pick it up automatically.

---

## Running tests
```bash
pytest tests/ -v
```

---

## Security

- API keys via `python-dotenv` with `override=True` — never hardcoded
- Prompt injection detection on all inputs
- Path traversal protection on all file writes
- Secret scrubbing before any LLM call
- Environment variable validation at boot
- Rate limiting on all Groq API calls

---

## Weekly Email Reminder

CareerPilot automatically emails you every Friday at 6PM PKT with your
current score, gaps, and a LinkedIn nudge — no laptop required.

Setup:
1. Make sure your Gmail API credentials are in `credentials/` (`credentials.json` and `token.json`)
2. Set `REMINDER_EMAIL_SENDER` and `REMINDER_EMAIL_RECEIVERS` in `config/.env`
3. Run `python scripts/send_gmail_api.py` to send a test email
4. (Recommended) Set up a cron job to run `python scripts/send_gmail_api.py` every Friday at 6PM

Example cron job (edit with `crontab -e`):
```
0 18 * * 5 cd /path/to/CareerPilot-Agent && /path/to/python3 scripts/send_gmail_api.py
```

No GitHub Actions or cloud automation is required — all reminders are sent locally from your machine.

---

## License

[MIT](LICENSE)
