# 🤖 CareerPilot

> A fully autonomous AI agent that watches your GitHub, tracks your skill gaps and coaches you toward landing your target internship, week over week.

---

## The Problem

Most students send out applications without really knowing where they stand. Which skills are you actually missing? Which of your projects would make a recruiter scroll past? Probably hard to say.

CareerPilot reads your GitHub and tells you. It scores your profile against your target role, points at specific gaps and nudges you the following week to see if you moved on them.

---

## How It Works

CareerPilot runs a continuous agentic loop across five stages:

```
Observe → Analyze → Remember → Plan → Act
```

| Stage | What happens |
|---|---|
| **Observe** | Reads your entire GitHub profile via the REST API |
| **Analyze** | LLM compares your profile against your target role and produces a consistent readiness score |
| **Remember** | Saves progress snapshots to SQLite for week-over-week tracking |
| **Plan** | Agent autonomously decides what skill or gap to address next |
| **Act** | Executes a skill from the registry and saves output to `output/` |

---

## Quickstart

```bash
git clone https://github.com/omerfarooq223/CareerPilot-Agent
cd CareerPilot-Agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp config/.env.example config/.env   # fill in your API keys
```

**Run the CLI agent:**

```bash
python agent.py
```

**Run the web UI:**

```bash
uvicorn api.server:app --reload --port 8000
# Then open http://localhost:8000
```

**Or try the live demo:** https://web-production-e1faa.up.railway.app

---

## Configuration

### `config/config.py`

Centralized configuration loader. Reads secrets from `config/.env` and defines app-wide constants.

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
| `suggest_project` | Suggests a mini-project targeting your biggest skill gap | `output/suggested_project.md` |
| `audit_repo` | Deep code audit via MCP if available, metadata fallback otherwise | `output/audit_<repo>.md` |
| `rewrite_readme` | Rewrites a repo's README to a professional standard | `output/readme_<repo>.md` |
| `generate_dev_card` | Generates a Markdown developer profile card | `output/developer_card.md` |
| `mock_interview_prep` | Produces role-specific interview questions | `output/mock_interview_prep.md` |
| `weekly_nudge` | Honest weekly progress report | `output/weekly_nudge.md` |
| `linkedin_writer` | LinkedIn post generator with post memory (HITL) | `output/linkedin_<type>_<repo>.md` |
| `update_goals` | Auto-syncs shipped projects and skills from GitHub | `config/goals.yaml` |

---

## Adding a New Skill

1. Create `skills/your_skill/your_skill.py`
2. Create `skills/your_skill/SKILL.md`
3. Register it in `actions/executor.py`:

```python
from skills.your_skill.your_skill import your_skill
registry.register("your_skill", "Description")(your_skill)
```

The planner and web UI pick it up automatically.

---

## Project Structure

```
CareerPilot-Agent/
├── agent.py                  # Main entrypoint: runs the agentic loop
├── AGENT.md                  # Agent architecture documentation
├── CLAUDE.md                 # AI assistant briefing and rules
├── LICENSE
├── Procfile                  # Railway deployment start command
├── README.md
├── pyproject.toml            # Python packaging and build config
├── railway.json              # Railway deployment config
├── requirements.txt
├── .gitignore
├── actions/                  # Action dispatcher and security
│   ├── error_handler.py      # Retry, timeout, fallback, rate limiting
│   ├── executor.py           # Skill dispatcher and output saving
│   └── security.py           # Input sanitization and path guards
├── api/                      # FastAPI backend
│   ├── server.py             # FastAPI app entrypoint
│   └── routes/
│       ├── __init__.py
│       ├── agent.py          # POST /api/run — full agentic loop
│       ├── dashboard.py      # GET /api/dashboard, history endpoints
│       └── skills.py         # POST /api/skills/{skill_name}
├── config/
│   ├── .env                  # Environment variables (never committed)
│   ├── config.py             # Centralized config loader
│   └── goals.yaml            # Target role, skills, companies
├── credentials/              # Gmail API credentials (gitignored)
│   ├── credentials.json
│   └── token.json
├── database/
│   └── db_utils.py           # SQLite connection pooling
├── frontend/
│   └── index.html            # Single-page HTML UI
├── memory/
│   ├── careerpilot.db        # SQLite DB (gitignored)
│   ├── github_cache.json     # GitHub API cache (gitignored)
│   ├── latest_snapshot.json  # Last committed agent state
│   ├── long_term.py          # Long-term memory logic
│   └── short_term.py         # Short-term/session memory logic
├── planner/
│   └── reasoner.py           # Groq-powered planning logic
├── scripts/
│   ├── careerpilot_daemon.py # Local daemon for weekly email
│   ├── send_gmail_api.py     # Sends email via Gmail API
│   └── weekly_reminder.py    # Email content builder
├── skills/
│   ├── registry.py           # Skill registration system
│   ├── audit_repo/
│   │   ├── SKILL.md
│   │   └── audit_repo.py
│   ├── dev_card/
│   │   ├── SKILL.md
│   │   └── dev_card.py
│   ├── gap_analyzer/
│   │   ├── SKILL.md
│   │   └── gap_analyzer.py
│   ├── github_observer/
│   │   ├── SKILL.md
│   │   └── github_observer.py
│   ├── goals_updater/
│   │   ├── SKILL.md
│   │   └── goals_updater.py
│   ├── interview_prep/
│   │   ├── SKILL.md
│   │   └── interview_prep.py
│   ├── linkedin_writer/
│   │   ├── SKILL.md
│   │   └── linkedin_writer.py
│   ├── nudge_writer/
│   │   ├── SKILL.md
│   │   └── nudge_writer.py
│   ├── project_suggester/
│   │   ├── SKILL.md
│   │   └── project_suggester.py
│   └── readme_writer/
│       ├── SKILL.md
│       └── readme_writer.py
└── tests/
    ├── test_memory.py
    ├── test_observer.py
    └── test_planner.py
```

---

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
| **Caching** | Local JSON (1-hour GitHub cache) |
| **Connection pooling** | SQLite (5 connections) |

---

## Security

- API keys loaded via `python-dotenv` — never hardcoded
- Prompt injection detection on all inputs
- Path traversal protection on all file writes
- Secrets scrubbed before any LLM call
- Environment variable validation at boot
- Rate limiting on all Groq API calls

---

## Weekly Email Reminder

CareerPilot emails you every Friday at 6PM PKT with your current score, identified gaps, and a LinkedIn nudge — no manual check-in needed.

**Setup:**

1. Place your Gmail API credentials in `credentials/` (`credentials.json` and `token.json`)
2. Set `REMINDER_EMAIL_SENDER` and `REMINDER_EMAIL_RECEIVERS` in `config/.env`
3. Test with: `python scripts/send_gmail_api.py`
4. Set up a weekly cron job:

```
0 18 * * 5 cd /path/to/CareerPilot-Agent && /path/to/python3 scripts/send_gmail_api.py
```

No GitHub Actions or cloud automation required — reminders run locally.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

[MIT](LICENSE)