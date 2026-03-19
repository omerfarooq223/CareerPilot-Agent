import sys, os, yaml
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pathlib import Path
from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action

GOALS_PATH = Path("config/goals.yaml")

# Skills detected in repos → maps to gap keywords to close
SKILL_SIGNALS = {
    "fastapi":  ["fastapi", "FastAPI"],
    "django":   ["django", "Django"],
    "docker":   ["docker", "Docker"],
    "pytorch":  ["pytorch", "PyTorch"],
    "tensorflow": ["tensorflow", "TensorFlow"],
    "flask":    ["flask", "Flask"],
}


def update_goals(session: SessionMemory) -> str:
    """
    Auto-update goals.yaml based on current GitHub profile:
    1. Add new repos to shipped_projects
    2. Close gaps that are now covered by shipped repos
    3. Update self_declared_skills based on repo topics/languages
    """
    logger.info("Action: update_goals")

    with open(GOALS_PATH) as f:
        goals = yaml.safe_load(f)

    changes = []

    # ── 1. Update shipped_projects ─────────────────────────────────
    existing_urls = {
        p.get("url", "").split("/")[-1].lower()
        for p in goals.get("shipped_projects", [])
    }

    new_projects = []
    for repo in session.profile.repos:
        repo_id = repo.name.lower()
        if repo_id not in existing_urls and repo.commit_count >= 2:
            new_projects.append({
                "name": repo.name,
                "type": _infer_type(repo),
                "url":  f"github.com/{os.getenv('GITHUB_USERNAME')}/{repo.name}",
                "stack": repo.topics if repo.topics else [repo.language or "Python"]
            })
            changes.append(f"Added to shipped_projects: {repo.name}")

    if new_projects:
        goals.setdefault("shipped_projects", []).extend(new_projects)

    # ── 2. Build demonstrated skills set ─────────────────────────
    demonstrated = set()
    for repo in session.profile.repos:
        name_lower   = repo.name.lower()
        topics_lower = [t.lower() for t in repo.topics]
        for skill, signals in SKILL_SIGNALS.items():
            for signal in signals:
                if signal.lower() in name_lower or signal.lower() in " ".join(topics_lower):
                    demonstrated.add(skill)

    # ── 3. Update self_declared_skills ────────────────────────────
    existing_skills = [s.lower() for s in goals.get("self_declared_skills", [])]
    new_skills = []

    skill_map = {
        "fastapi":   "FastAPI",
        "django":    "Django",
        "docker":    "Docker",
        "pytorch":   "PyTorch",
        "tensorflow":"TensorFlow",
    }

    for skill_key, skill_label in skill_map.items():
        if skill_key in demonstrated and skill_key not in existing_skills:
            new_skills.append(skill_label)
            changes.append(f"Added to skills: {skill_label}")

    if new_skills:
        goals.setdefault("self_declared_skills", []).extend(new_skills)

    # ── Save updated goals.yaml ───────────────────────────────────
    with open(GOALS_PATH, "w") as f:
        yaml.dump(goals, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    log_action("update_goals", f"{len(changes)} changes made")
    session.remember_action("update_goals")

    if changes:
        logger.success(f"goals.yaml updated — {len(changes)} changes")
        return "## goals.yaml Updated\n\n" + "\n".join(f"- {c}" for c in changes)
    else:
        logger.info("goals.yaml — no changes needed")
        return "## goals.yaml — No Changes\n\nEverything is already up to date."


def _infer_type(repo) -> str:
    """Infer project type from repo topics and language."""
    topics = [t.lower() for t in repo.topics]
    name   = repo.name.lower()

    if any(t in topics + [name] for t in ["agent", "agentic", "llm", "groq"]):
        return "Agentic AI"
    if any(t in topics + [name] for t in ["yolo", "opencv", "vision", "detection"]):
        return "Computer Vision"
    if any(t in topics + [name] for t in ["ml", "sklearn", "classification"]):
        return "Machine Learning"
    if any(t in topics + [name] for t in ["fastapi", "django", "api", "backend"]):
        return "Backend / API"
    if any(t in topics + [name] for t in ["n8n", "automation", "workflow"]):
        return "Automation"
    return "Python Project"