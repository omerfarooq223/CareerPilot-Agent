import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Callable
from loguru import logger
from pydantic import BaseModel


# ── Skill definition ───────────────────────────────────────────────────────────

class Skill(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    fn: Callable = None         # the actual function to call

    class Config:
        arbitrary_types_allowed = True


# ── Registry ───────────────────────────────────────────────────────────────────

class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, name: str, description: str, version: str = "1.0.0"):
        """Decorator to register a function as a skill."""
        def decorator(fn: Callable):
            skill = Skill(
                name=name,
                description=description,
                version=version,
                enabled=True,
                fn=fn
            )
            self._skills[name] = skill
            logger.debug(f"Skill registered: {name} v{version}")
            return fn
        return decorator

    def enable(self, name: str):
        if name in self._skills:
            self._skills[name].enabled = True
            logger.info(f"Skill enabled: {name}")

    def disable(self, name: str):
        if name in self._skills:
            self._skills[name].enabled = False
            logger.info(f"Skill disabled: {name}")

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def call(self, name: str, *args, **kwargs):
        """Call a skill by name with safety checks."""
        skill = self._skills.get(name)
        if not skill:
            logger.error(f"Skill not found: {name}")
            raise ValueError(f"Skill '{name}' is not registered")
        if not skill.enabled:
            logger.warning(f"Skill is disabled: {name}")
            raise RuntimeError(f"Skill '{name}' is currently disabled")
        logger.info(f"Calling skill: {name} v{skill.version}")
        return skill.fn(*args, **kwargs)

    def list_all(self) -> list[dict]:
        """Return a summary of all registered skills."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
                "enabled": s.enabled
            }
            for s in self._skills.values()
        ]

    def list_enabled(self) -> list[str]:
        """Return names of all enabled skills."""
        return [s.name for s in self._skills.values() if s.enabled]


# ── Global registry instance ───────────────────────────────────────────────────

registry = SkillRegistry()