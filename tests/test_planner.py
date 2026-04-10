import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.short_term import SessionMemory
from planner.reasoner import make_plan, AgentPlan
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

def test_plan_returns_correct_type():
    session = SessionMemory()
    session.gap_report = MOCK_REPORT
    plan = make_plan(session)
    assert isinstance(plan, AgentPlan)

def test_plan_has_actions():
    session = SessionMemory()
    session.gap_report = MOCK_REPORT
    plan = make_plan(session)
    assert len(plan.actions_to_take) > 0

def test_plan_has_priority_action():
    session = SessionMemory()
    session.gap_report = MOCK_REPORT
    plan = make_plan(session)
    assert plan.priority_action in plan.actions_to_take