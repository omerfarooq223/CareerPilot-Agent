from pydantic import BaseModel
from typing import Optional
from skills.github_observer.github_observer import GitHubProfile
from skills.gap_analyzer.gap_analyzer import GapReport


class SessionMemory(BaseModel):
    """Holds everything the agent knows in the current run."""
    profile: Optional[GitHubProfile] = None
    gap_report: Optional[GapReport] = None
    actions_taken: list[str] = []
    notes: list[str] = []

    def remember_action(self, action: str):
        self.actions_taken.append(action)

    def add_note(self, note: str):
        self.notes.append(note)

    def summarize(self) -> str:
        return (
            f"Profile: {self.profile.username if self.profile else 'not loaded'}\n"
            f"Hirability score: {self.gap_report.overall_score if self.gap_report else 'not analyzed'}/10\n"
            f"Actions taken this session: {len(self.actions_taken)}\n"
            f"Notes: {len(self.notes)}"
        )
