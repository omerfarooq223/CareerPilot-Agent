import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.long_term import init_db, save_snapshot, get_last_snapshot, get_score_history
from skills.gap_analyzer.gap_analyzer import GapReport

MOCK_REPORT = GapReport(
    strengths=["Python", "AI/ML"],
    critical_gaps=["FastAPI", "Docker"],
    nice_to_have=["PyTorch"],
    top_3_actions=["Build FastAPI project", "Learn Docker", "Add tests"],
    portfolio_ready_repos=["AutoGrader-Agent"],
    weakest_repos=["DSA_CPP"],
    overall_score=7,
    verdict="Solid candidate with addressable gaps."
)

def test_db_initializes():
    init_db()
    assert os.path.exists("memory/careerpilot.db")

def test_save_and_retrieve_snapshot():
    init_db()
    save_snapshot(MOCK_REPORT)
    snapshot = get_last_snapshot()
    assert snapshot is not None
    assert snapshot["overall_score"] == 7
    assert "FastAPI" in snapshot["critical_gaps"]

def test_score_history_grows():
    init_db()
    before = len(get_score_history())
    save_snapshot(MOCK_REPORT)
    after = len(get_score_history())
    assert after == before + 1
