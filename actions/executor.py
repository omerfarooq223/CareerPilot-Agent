import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq
from memory.short_term import SessionMemory
from memory.long_term import log_action
from actions.error_handler import retry, timeout, sanitize_input, groq_limiter
from actions.security import safe_output_path, scrub_secrets, check_prompt_injection
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / "config" / ".env", override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Shared utilities (used by all skills) ──────────────────────────────────────

@retry(max_attempts=3, delay=2.0)
@timeout(seconds=30)
def call_groq(prompt: str, max_tokens: int = 2000) -> str:
    groq_limiter.wait()
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": sanitize_input(prompt)}],
        temperature=0.5,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content.strip()


def save_output(filename: str, content: str) -> Path:
    path = safe_output_path(filename)         # path traversal guard
    content = scrub_secrets(content)          # scrub any leaked secrets
    path.write_text(content, encoding="utf-8")
    logger.success(f"Saved → {path}")
    return path


# ── Register all skills ────────────────────────────────────────────────────────

from skills.project_suggester.project_suggester import suggest_project
from skills.audit_repo.audit_repo import audit_repo
from skills.readme_writer.readme_writer import rewrite_readme
from skills.dev_card.dev_card import generate_dev_card
from skills.interview_prep.interview_prep import mock_interview_prep
from skills.nudge_writer.nudge_writer import weekly_nudge
from skills.linkedin_writer.linkedin_writer import linkedin_writer
from skills.registry import registry

# ── Register all skills into the registry ─────────────────────────────────────
registry.register("suggest_project",    "Suggest a mini-project to fill skill gaps")(suggest_project)
registry.register("audit_repo",         "Deep audit a repo for quality issues")(audit_repo)
registry.register("rewrite_readme",     "Rewrite a repo README professionally")(rewrite_readme)
registry.register("generate_dev_card",  "Generate a markdown developer profile card")(generate_dev_card)
registry.register("mock_interview_prep","Generate role-specific interview questions")(mock_interview_prep)
registry.register("weekly_nudge",       "Write an honest weekly progress report")(weekly_nudge)
registry.register("linkedin_writer", "Generate and approve LinkedIn posts with HITL flow")(linkedin_writer)

# ── Dispatcher ─────────────────────────────────────────────────────────────────

def execute_plan(actions: list[str], session: SessionMemory):
    """Execute a list of actions using the skill registry."""
    for action in actions:
        try:
            logger.info(f"Executing skill: {action}")
            result = registry.call(action, session)
            print(f"\n{'─'*60}")
            print(f"✅ {action.upper()}")
            print('─'*60)
            print(result)
        except ValueError as e:
            logger.error(f"Unknown skill: {e}")
        except RuntimeError as e:
            logger.warning(f"Skill skipped: {e}")
        except Exception as e:
            logger.error(f"Skill {action} failed: {e}")