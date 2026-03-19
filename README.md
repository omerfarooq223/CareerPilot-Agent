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
git clone https://github.com/omerfarooq223/careerpilot
cd careerpilot
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

---

## Configuration

### `config/.env`
```
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your_github_username
GROQ_API_KEY=gsk_...
```

### `config/goals.yaml`
```yaml
model_provider: "groq"
model_name: "llama-3.3-70b-versatile"
target_role: "AI/ML Intern"
target_timeline: "3 months"
target_companies:
  - "Arbisoft"
  - "Folio3"
self_declared_skills:
  - "Python"
  - "Agentic AI"
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

---

## Project structure
```
careerpilot/
├── agent.py                        # CoreAgent — boots the full CLI loop
├── CLAUDE.md                       # This file — AI assistant briefing
├── AGENT.md                        # Agent architecture documentation
├── README.md                       # Public-facing project documentation
├── pyproject.toml                  # Packaging and dependency config
├── requirements.txt                # Pinned dependencies
├── config/
│   ├── .env                        # Secrets — NEVER commit this
│   └── goals.yaml                  # User's target role, skills, companies
├── skills/
│   ├── registry.py                 # Plug-and-play skill registration system
│   ├── github_observer/
│   │   ├── github_observer.py      # Fetches GitHub profile via REST API
│   │   └── SKILL.md
│   ├── gap_analyzer/
│   │   ├── gap_analyzer.py         # Groq-powered gap analysis
│   │   └── SKILL.md
│   ├── audit_repo/
│   │   ├── audit_repo.py           # Smart audit — MCP deep if available, metadata fallback
│   │   └── SKILL.md
│   ├── project_suggester/
│   │   ├── project_suggester.py    # Suggests mini-projects for skill gaps
│   │   └── SKILL.md
│   ├── readme_writer/
│   │   ├── readme_writer.py        # Rewrites READMEs professionally
│   │   └── SKILL.md
│   ├── dev_card/
│   │   ├── dev_card.py             # Generates developer profile card
│   │   └── SKILL.md
│   ├── interview_prep/
│   │   ├── interview_prep.py       # Mock interview questions
│   │   └── SKILL.md
│   ├── nudge_writer/
│   │   ├── nudge_writer.py         # Weekly honest progress nudge
│   │   └── SKILL.md
│   └── linkedin_writer/
│       ├── linkedin_writer.py      # HITL LinkedIn post generator with memory
│       └── SKILL.md
├── memory/
│   ├── short_term.py               # SessionMemory — current run state
│   └── long_term.py                # SQLite — snapshots, action log, LinkedIn history
├── planner/
│   └── reasoner.py                 # Groq-powered autonomous planner
├── actions/
│   ├── executor.py                 # Skill dispatcher + shared utilities
│   ├── error_handler.py            # Retry, timeout, fallback, rate limiting
│   └── security.py                 # Input sanitization, path guards, secret scrubbing
├── api/
│   ├── server.py                   # FastAPI app — serves UI and skill endpoints
│   └── routes/
│       ├── dashboard.py            # GET /api/dashboard, history endpoints
│       ├── skills.py               # POST /api/skills/{skill_name}
│       └── agent.py                # POST /api/run — full autonomous loop
├── frontend/
│   └── index.html                  # Single-page web UI (Arctic White theme)
├── output/                         # Generated files — gitignored
└── tests/
    ├── test_observer.py
    ├── test_memory.py
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
| **Error handling** | Custom retry/timeout/fallback decorators |
| **Security** | Prompt injection guard, path traversal protection |
| **Testing** | pytest |

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

## License

MIT