import os
import requests
from loguru import logger
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / "config" / ".env", override=True)

BASE_URL = "https://api.github.com"

def _get_headers():
    """Get headers dynamically so Railway env vars are always picked up."""
    token = os.getenv("GITHUB_TOKEN")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def _get_username():
    return os.getenv("GITHUB_USERNAME", "")


# ── Data models ────────────────────────────────────────────────────────────────

class RepoSnapshot(BaseModel):
    name: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    last_updated: str
    has_readme: bool
    topics: list[str]
    url: str
    commit_count: int


class GitHubProfile(BaseModel):
    username: str
    name: Optional[str]
    bio: Optional[str]
    followers: int
    public_repos: int
    repos: list[RepoSnapshot]
    languages_used: dict[str, int]   # language → repo count
    total_commits_sampled: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_commit_count(repo_name: str) -> int:
    """Get total commit count for a repo (sampled via pagination header)."""
    url = f"{BASE_URL}/repos/{GITHUB_USERNAME}/{repo_name}/commits?per_page=1"
    response = requests.get(url, headers=_get_headers())
    if response.status_code != 200:
        return 0
    # GitHub returns total count in Link header
    link = response.headers.get("Link", "")
    if 'rel="last"' in link:
        try:
            last_page = link.split('rel="last"')[0]
            page_num = last_page.split("page=")[-1].split(">")[0]
            return int(page_num)
        except Exception:
            return 1
    return len(response.json())  # fallback: less than 30 commits


def has_readme(repo_name: str) -> bool:
    """Check if a repo has a README file."""
    url = f"{BASE_URL}/repos/{GITHUB_USERNAME}/{repo_name}/readme"
    response = requests.get(url, headers=_get_headers())
    return response.status_code == 200


# ── Main observer ──────────────────────────────────────────────────────────────

def fetch_github_profile() -> GitHubProfile:
    """Fetch full GitHub profile and all repo snapshots."""
    logger.info(f"Fetching GitHub profile for: {_get_username()}")

    # Get user info
    user_resp = requests.get(f"{BASE_URL}/users/{_get_username()}", headers=_get_headers())
    user_resp.raise_for_status()
    user = user_resp.json()

    # Get all repos
    repos_resp = requests.get(
        f"{BASE_URL}/users/{_get_username()}/repos?per_page=100&sort=updated",
        headers=HEADERS
    )
    repos_resp.raise_for_status()
    raw_repos = repos_resp.json()

    repos = []
    languages_used: dict[str, int] = {}
    total_commits = 0

    for repo in raw_repos:
        name = repo["name"]
        language = repo.get("language")
        commit_count = get_commit_count(name)
        readme = has_readme(name)
        total_commits += commit_count

        if language:
            languages_used[language] = languages_used.get(language, 0) + 1

        snapshot = RepoSnapshot(
            name=name,
            description=repo.get("description"),
            language=language,
            stars=repo.get("stargazers_count", 0),
            forks=repo.get("forks_count", 0),
            last_updated=repo.get("updated_at", ""),
            has_readme=readme,
            topics=repo.get("topics", []),
            url=repo.get("html_url", ""),
            commit_count=commit_count
        )
        repos.append(snapshot)
        logger.info(f"  ✓ {name} | {language} | {commit_count} commits | README: {readme}")

    profile = GitHubProfile(
        username=user.get("login", GITHUB_USERNAME),
        name=user.get("name"),
        bio=user.get("bio"),
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        repos=repos,
        languages_used=languages_used,
        total_commits_sampled=total_commits
    )

    logger.success(f"Profile built — {len(repos)} repos found")
    return profile


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.pretty import pprint
    profile = fetch_github_profile()
    pprint(profile.model_dump())
