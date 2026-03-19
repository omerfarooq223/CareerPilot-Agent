import sys, os, sqlite3, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import APIRouter
from memory.long_term import init_db, get_last_snapshot, get_score_history, get_linkedin_post_history, DB_PATH

router = APIRouter()

@router.get("/dashboard")
def get_dashboard():
    init_db()
    snapshot  = get_last_snapshot()
    history   = get_score_history()
    linkedin  = get_linkedin_post_history()

    return {
        "score":          snapshot["overall_score"] if snapshot else None,
        "strengths":      snapshot["strengths"]     if snapshot else [],
        "critical_gaps":  snapshot["critical_gaps"] if snapshot else [],
        "top_3_actions":  snapshot["top_3_actions"] if snapshot else [],
        "portfolio_repos":snapshot["portfolio_ready_repos"] if snapshot else [],
        "verdict":        snapshot["verdict"]        if snapshot else None,
        "score_history":  history,
        "linkedin_posts": linkedin,
        "total_sessions": len(history),
    }

@router.get("/history/audits")
def get_audit_history():
    """Return all past audit and skill outputs from action log."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, action_type, description
        FROM actions_log
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()
    return {
        "history": [
            {"timestamp": r[0], "action": r[1], "description": r[2]}
            for r in rows
        ]
    }

@router.get("/history/outputs")
def get_output_files():
    """Return list of generated output files."""
    output_dir = "output"
    files = []
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir), reverse=True):
            if f.endswith(".md"):
                path = os.path.join(output_dir, f)
                stat = os.stat(path)
                files.append({
                    "filename": f,
                    "size_kb":  round(stat.st_size / 1024, 1),
                    "modified": stat.st_mtime,
                })
    return {"files": files}

@router.get("/history/outputs/{filename}")
def get_output_file(filename: str):
    """Return the content of a specific output file."""
    safe_name = os.path.basename(filename)
    path = os.path.join("output", safe_name)
    if not os.path.exists(path):
        return {"content": None, "error": "File not found"}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": safe_name, "content": content}

@router.get("/history/linkedin")
def get_linkedin_history():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, post_type, repo_name, post_content, status
        FROM linkedin_posts ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {"posts": [{"id":r[0],"timestamp":r[1],"post_type":r[2],
            "repo_name":r[3],"post_content":r[4],"status":r[5]} for r in rows]}

@router.get("/history/memory")
def get_full_memory():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    output_dir = "output"
    categories = {"projects":[],"audits":[],"readmes":[],"dev_cards":[],"interview":[],"nudges":[],"other":[]}
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir), reverse=True):
            if not f.endswith(".md"): continue
            path = os.path.join(output_dir, f)
            stat = os.stat(path)
            item = {"filename":f,"label":f.replace('.md','').replace('_',' ').title(),
                    "size_kb":round(stat.st_size/1024,1),"modified":stat.st_mtime}
            if f.startswith("suggested"):   categories["projects"].append(item)
            elif "audit" in f:              categories["audits"].append(item)
            elif f.startswith("readme"):    categories["readmes"].append(item)
            elif f.startswith("developer"): categories["dev_cards"].append(item)
            elif f.startswith("mock"):      categories["interview"].append(item)
            elif f.startswith("weekly"):    categories["nudges"].append(item)
            else:                           categories["other"].append(item)
    cursor.execute("""
        SELECT id, timestamp, post_type, repo_name, post_content, status
        FROM linkedin_posts ORDER BY timestamp DESC
    """)
    linkedin_rows = cursor.fetchall()
    conn.close()
    return {
        "categories": categories,
        "linkedin_posts": [{"id":r[0],"timestamp":r[1],"post_type":r[2],
            "repo_name":r[3],"post_content":r[4],"status":r[5]} for r in linkedin_rows]
    }