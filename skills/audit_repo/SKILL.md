# Skill: audit_repo

## What it does
Audits a GitHub repo. Automatically tries to read actual code via GitHub MCP
server for a deep code review. Falls back to metadata-based audit if MCP is
unavailable — so it always works regardless of setup.

## Inputs
- `session.gap_report.weakest_repos` — auto-selects if no repo specified
- `session.profile.repos` — full repo details
- Optional: explicit `repo_name` argument

## Outputs
- `output/audit_<repo_name>.md` — full audit report
- `output/audit_<repo_name>_comparison.md` — comparison with previous audit (only if a previous one exists)

## When the planner should use this
- When `weakest_repos` list is non-empty
- When a repo has low commit count or no topics
- Not more than once per repo per session

## Dependencies
- Groq API
- GitHub REST API (always)
- GitHub MCP server (optional — enables deep code reading)

## Version
2.1.0