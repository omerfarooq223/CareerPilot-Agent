import requests
import json
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from pydantic import BaseModel
from config.config import Config
from actions.circuit_breaker import circuit_breaker

CACHE_PATH = Config.GITHUB_CACHE_PATH
CACHE_TTL_HOURS = Config.GITHUB_CACHE_TTL_HOURS
BASE_URL = Config.GITHUB_BASE_URL

def _get_headers():
    """Get headers dynamically from Config."""
    token = Config.GITHUB_TOKEN
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def _get_username():
    return Config.GITHUB_USERNAME


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

@circuit_breaker("github_commits", failure_threshold=Config.CB_FAILURE_THRESHOLD, recovery_timeout=Config.CB_RECOVERY_TIMEOUT)
def get_commit_count(repo_name: str) -> int:
    """Get total commit count for a repo (sampled via pagination header)."""
    url = f"{BASE_URL}/repos/{_get_username()}/{repo_name}/commits?per_page=1"
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


@circuit_breaker("github_readme", failure_threshold=Config.CB_FAILURE_THRESHOLD, recovery_timeout=Config.CB_RECOVERY_TIMEOUT)
def has_readme(repo_name: str) -> bool:
    """Check if a repo has a README file."""
    url = f"{BASE_URL}/repos/{_get_username()}/{repo_name}/readme"
    response = requests.get(url, headers=_get_headers())
    return response.status_code == 200


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> GitHubProfile | None:
    """Load cached GitHub profile if it exists and is fresh."""
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text())
        cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
        if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
            logger.debug("GitHub cache expired")
            return None
        logger.info("Using cached GitHub profile")
        del data["_cached_at"]
        return GitHubProfile(**data)
    except Exception as e:
        logger.debug(f"Cache load failed: {e}")
        return None


def _save_cache(profile: GitHubProfile) -> None:
    """Save GitHub profile to cache with timestamp."""
    try:
        data = profile.model_dump()
        data["_cached_at"] = datetime.now().isoformat()
        CACHE_PATH.write_text(json.dumps(data, default=str))
        logger.debug(f"GitHub profile cached → {CACHE_PATH}")
    except Exception as e:
        logger.debug(f"Cache save failed: {e}")


# ── Main observer ──────────────────────────────────────────────────────────────

@circuit_breaker("github_profile", failure_threshold=Config.CB_FAILURE_THRESHOLD, recovery_timeout=Config.CB_RECOVERY_TIMEOUT)
def fetch_github_profile(force_refresh: bool = False) -> GitHubProfile:
    """
    Fetch full GitHub profile and all repo snapshots.
    Uses a 1-hour local cache to avoid redundant API calls.
    Set force_refresh=True to bypass cache.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return cached

    logger.info(f"Fetching GitHub profile for: {_get_username()}")

    # Get user info
    user_resp = requests.get(f"{BASE_URL}/users/{_get_username()}", headers=_get_headers())
    user_resp.raise_for_status()
    user = user_resp.json()

    # Get all repos
    repos_resp = requests.get(
        f"{BASE_URL}/users/{_get_username()}/repos?per_page=100&sort=updated",
        headers=_get_headers()
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
        username=user.get("login", _get_username()),
        name=user.get("name"),
        bio=user.get("bio"),
        followers=user.get("followers", 0),
        public_repos=user.get("public_repos", 0),
        repos=repos,
        languages_used=languages_used,
        total_commits_sampled=total_commits
    )

    logger.success(f"Profile built — {len(repos)} repos found")
    _save_cache(profile)
    return profile


# ── Quick test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from rich.pretty import pprint
    profile = fetch_github_profile()
    pprint(profile.model_dump())
