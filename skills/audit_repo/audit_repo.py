import sys, os, json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from loguru import logger
from memory.short_term import SessionMemory
from memory.long_term import log_action


def audit_repo(session: SessionMemory, repo_name: str = None) -> str:
    from actions.executor import call_groq, save_output

    logger.info("Action: audit_repo")

    if not repo_name and session.gap_report and session.gap_report.weakest_repos:
        repo_name = session.gap_report.weakest_repos[0]
    elif not repo_name:
        repo_name = session.profile.repos[0].name if session.profile else "unknown"

    repo_details = {}
    if session.profile:
        for r in session.profile.repos:
            if r.name == repo_name:
                repo_details = r.model_dump()
                break

    # Check if this repo has been audited before
    previous_audit = _load_previous_audit(repo_name)

    # Try MCP deep audit first, fall back to metadata
    file_context = _try_mcp_read(repo_name)

    if file_context:
        logger.info(f"Deep audit via MCP: {repo_name}")
        prompt = _deep_prompt(repo_name, repo_details, file_context)
    else:
        logger.info(f"Metadata audit (MCP unavailable): {repo_name}")
        prompt = _metadata_prompt(repo_name, repo_details)

    # Run the new audit
    new_audit = call_groq(prompt)
    save_output(f"audit_{repo_name}.md", new_audit)
    log_action("audit_repo", f"Audited: {repo_name} ({'deep' if file_context else 'metadata'})")

    # If previous audit exists — run comparison
    if previous_audit:
        logger.info(f"Previous audit found for {repo_name} — running comparison")
        comparison = _compare_audits(repo_name, previous_audit, new_audit, call_groq)
        save_output(f"audit_{repo_name}_comparison.md", comparison)
        log_action("audit_comparison", f"Compared audits for: {repo_name}")
        session.remember_action("audit_repo")
        # Return both combined
        return f"{new_audit}\n\n---\n\n{comparison}"

    session.remember_action("audit_repo")
    return new_audit


def _load_previous_audit(repo_name: str) -> str | None:
    """Load previous audit from output/ if it exists."""
    path = Path("output") / f"audit_{repo_name}.md"
    if path.exists():
        content = path.read_text(encoding="utf-8")
        # Only use it if it has meaningful content
        if len(content) > 200:
            logger.info(f"Previous audit loaded: {path}")
            return content
    return None


def _compare_audits(repo_name: str, previous: str, current: str, call_groq) -> str:
    """Ask Groq to compare old vs new audit and identify what changed."""
    prompt = f"""
You are a senior developer reviewing two audits of the same GitHub repo over time.
Compare them and identify concrete progress.

Repo: {repo_name}

--- PREVIOUS AUDIT ---
{previous[:2000]}

--- CURRENT AUDIT ---
{current[:2000]}

Write a comparison report covering:

## Audit Comparison: {repo_name}

### What Was Fixed
(specific improvements made since the last audit — be concrete)

### Still Needs Work
(issues that were flagged before and are still present)

### New Issues Found
(problems that weren't in the previous audit)

### Progress Score
(rate improvement: Significant / Moderate / Minimal / Declined)

### Verdict
(one honest paragraph — has the developer acted on the feedback?)
"""
    return call_groq(prompt, max_tokens=1200)


def _try_mcp_read(repo_name: str) -> dict | None:
    """Attempt to read actual file contents via MCP. Returns None if unavailable."""
    try:
        import asyncio
        from dotenv import load_dotenv
        load_dotenv(
            dotenv_path=Path(__file__).resolve().parent.parent.parent / "config" / ".env",
            override=True
        )
        import os
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
        GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")

        async def _read():
            params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN}
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    contents_result = await session.call_tool("get_file_contents", {
                        "owner": GITHUB_USERNAME, "repo": repo_name, "path": ""
                    })
                    contents = "\n".join(
                        b.text for b in contents_result.content if hasattr(b, "text")
                    )

                    main_code = ""
                    for candidate in ["main.py", "app.py", "agent.py", "index.py"]:
                        try:
                            r = await session.call_tool("get_file_contents", {
                                "owner": GITHUB_USERNAME, "repo": repo_name, "path": candidate
                            })
                            main_code = f"### {candidate}\n" + "\n".join(
                                b.text for b in r.content if hasattr(b, "text")
                            )[:2000]
                            break
                        except Exception:
                            continue

                    readme = ""
                    try:
                        r = await session.call_tool("get_file_contents", {
                            "owner": GITHUB_USERNAME, "repo": repo_name, "path": "README.md"
                        })
                        readme = "\n".join(
                            b.text for b in r.content if hasattr(b, "text")
                        )[:1500]
                    except Exception:
                        pass

                    return {"contents": contents, "main_code": main_code, "readme": readme}

        return asyncio.run(_read())

    except Exception as e:
        logger.debug(f"MCP unavailable, falling back to metadata audit: {e}")
        return None


def _deep_prompt(repo_name: str, repo_details: dict, file_context: dict) -> str:
    return f"""
You are a senior software engineer doing a DEEP code review with access to actual code.

Repo: {repo_name}
Details: {json.dumps(repo_details, indent=2)}

--- REPO STRUCTURE ---
{file_context.get('contents','')[:1500]}

--- README ---
{file_context.get('readme','No README found.')}

--- MAIN CODE ---
{file_context.get('main_code','No main file found.')}

## Repo Audit: {repo_name}

### Code Quality (rate 1-10)
(observations from actual code — naming, structure, complexity)

### Architecture Assessment
(separation of concerns, modularity, readability)

### README vs Reality
(does README match what the code actually does?)

### Specific Issues Found
(concrete problems — patterns, missing docs, no tests, etc.)

### What Would Impress a Senior Dev
(genuinely good things about this code)

### 5 Specific Improvements
(exact, actionable — not generic advice)

### Hirability Signal
(what does this repo tell an interviewer about the developer?)
"""


def _metadata_prompt(repo_name: str, repo_details: dict) -> str:
    return f"""
You are a senior software engineer auditing a GitHub repo based on its metadata.

Repo: {repo_name}
Details: {json.dumps(repo_details, indent=2)}

## Repo Audit: {repo_name}

### Overall Impression
(2-3 sentences based on description, language, topics)

### README Quality
(rate 1-10 and explain what's missing)

### Code Quality Signals
(inferred from language, commit count, topics)

### What's Missing
(tests, CI/CD, docs, license, contributing guide)

### How to Make It Portfolio-Ready
(step-by-step specific improvements)

### Estimated Time to Fix
(realistic estimate)
"""