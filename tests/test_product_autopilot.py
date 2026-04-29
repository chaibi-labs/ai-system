import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("product_autopilot", ROOT / "scripts" / "product_autopilot.py")
product_autopilot = importlib.util.module_from_spec(spec)
sys.modules["product_autopilot"] = product_autopilot
assert spec.loader is not None
spec.loader.exec_module(product_autopilot)

Issue = product_autopilot.Issue
choose_issue = product_autopilot.choose_issue
choose_issues = product_autopilot.choose_issues
build_worker_prompt = product_autopilot.build_worker_prompt


def issue(number, title, labels=(), created="2026-01-01T00:00:00Z"):
    return Issue(
        number=number,
        title=title,
        body="",
        labels=tuple(labels),
        html_url=f"https://github.com/chaibi-labs/pregnancy-food-checker/issues/{number}",
        created_at=created,
        updated_at=created,
    )


def test_choose_issue_skips_anis_decision_and_cost_blockers():
    issues = [
        issue(1, "Needs token", ["priority:P1", "decision:anis"]),
        issue(2, "Paid lookup", ["priority:P1", "cost:approval-required"]),
        issue(3, "Safe UI polish", ["priority:P2"]),
    ]

    selected = choose_issue(issues)

    assert selected is not None
    assert selected.number == 3


def test_choose_issue_honors_priority_then_age():
    issues = [
        issue(1, "Older P3", ["priority:P3"], "2026-01-01T00:00:00Z"),
        issue(2, "Newer P1", ["priority:P1"], "2026-02-01T00:00:00Z"),
        issue(3, "Older P2", ["priority:P2"], "2026-01-15T00:00:00Z"),
    ]

    selected = choose_issue(issues)

    assert selected is not None
    assert selected.number == 2


def test_specific_blocked_issue_is_not_selected():
    issues = [issue(10, "Needs Anis", ["decision:anis"])]

    assert choose_issue(issues, issue_number=10) is None


def test_worker_prompt_contains_hard_stops_and_po_merge_gates():
    product = {"repo": "chaibi-labs/pregnancy-food-checker", "po_agent": "po-pregnancy-food-checker"}
    prompt = build_worker_prompt("pregnancy-food-checker", product, issue(9, "Do thing", ["priority:P2"]))

    assert "python3 /tmp/ai-system-po/scripts/po_github.py validate pregnancy-food-checker" in prompt
    assert "Stop and return BLOCKED" in prompt
    assert "cost" in prompt
    assert "API tokens/secrets" in prompt
    assert "PO merge gates" in prompt
    assert "CI/checks: pass/fail" in prompt
    assert "sourcing ~/.ai-system/secrets/po-pregnancy-food-checker.env" in prompt


def test_choose_issues_returns_bounded_serial_batch():
    issues = [
        issue(1, "Needs token", ["priority:P1", "decision:anis"]),
        issue(2, "First safe", ["priority:P1"], "2026-01-02T00:00:00Z"),
        issue(3, "Second safe", ["priority:P2"], "2026-01-01T00:00:00Z"),
        issue(4, "Third safe", ["priority:P3"], "2026-01-01T00:00:00Z"),
    ]

    selected = choose_issues(issues, max_issues=2)

    assert [item.number for item in selected] == [2, 3]


def test_choose_issues_with_specific_issue_ignores_batch_size():
    issues = [
        issue(2, "First safe", ["priority:P1"]),
        issue(3, "Second safe", ["priority:P2"]),
    ]

    selected = choose_issues(issues, max_issues=5, issue_number=3)

    assert [item.number for item in selected] == [3]


def test_worker_prompt_repairs_internal_failures_before_blocking():
    product = {"repo": "chaibi-labs/pregnancy-food-checker", "po_agent": "po-pregnancy-food-checker"}
    prompt = build_worker_prompt("pregnancy-food-checker", product, issue(11, "Fix thing", ["priority:P2"]))

    assert "Stop and return BLOCKED only for external gates" in prompt
    assert "internal fixable failures" in prompt
    assert "up to 3 focused repair attempts" in prompt
    assert "If CI fails, inspect logs, repair, push" in prompt
    assert "repair attempts used" in prompt
