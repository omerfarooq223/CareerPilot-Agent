import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from skills.github_observer.github_observer import fetch_github_profile, GitHubProfile, RepoSnapshot

def test_profile_returns_correct_type():
    profile = fetch_github_profile()
    assert isinstance(profile, GitHubProfile)

def test_profile_has_repos():
    profile = fetch_github_profile()
    assert len(profile.repos) > 0

def test_each_repo_is_valid():
    profile = fetch_github_profile()
    for repo in profile.repos:
        assert isinstance(repo, RepoSnapshot)
        assert repo.name != ""
        assert repo.url.startswith("https://github.com")

def test_languages_populated():
    profile = fetch_github_profile()
    assert isinstance(profile.languages_used, dict)
    assert len(profile.languages_used) > 0