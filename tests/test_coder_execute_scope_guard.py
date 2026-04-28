import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.coder_execute import (
    collect_staged_diff_stats,
    parse_expected_diff_budget,
    scope_guard_violations,
)


class TestCoderExecuteScopeGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.run_git("init")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "Test User")
        (self.temp_dir / "scripts").mkdir()
        (self.temp_dir / "scripts/coder_execute.py").write_text("line1\nline2\nline3\n")
        self.run_git("add", ".")
        self.run_git("commit", "-m", "baseline")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def run_git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=self.temp_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    def stage_file(self, rel: str, content: str) -> None:
        path = self.temp_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.run_git("add", rel)

    def base_task_spec(self, budget: object) -> dict:
        return {
            "files_to_create_or_edit": ["scripts/coder_execute.py"],
            "expected_diff_shape": [{"scripts/coder_execute.py": budget}],
        }

    def test_over_budget_rewrite_is_blocked(self):
        task_spec = self.base_task_spec(
            "~2 inserted lines only, preserve/no-other-edits language, and many deletions"
        )
        self.stage_file("scripts/coder_execute.py", "new1\nnew2\nnew3\nnew4\nnew5\n")

        violations = scope_guard_violations(task_spec, self.temp_dir)

        self.assertTrue(any("deleted lines" in v for v in violations))
        self.assertTrue(any("rewrite/delete blocked" in v for v in violations))

    def test_within_budget_insertion_is_allowed(self):
        task_spec = self.base_task_spec("~180 added lines, ~60 deleted lines max")
        self.stage_file("scripts/coder_execute.py", "line1\nline2\nline3\nadded\n")

        violations = scope_guard_violations(task_spec, self.temp_dir)

        self.assertEqual([], violations)

    def test_staged_edits_to_a_file_outside_task_spec_are_blocked(self):
        task_spec = self.base_task_spec("~180 added lines, ~60 deleted lines max")
        self.stage_file("README.md", "outside scope\n")

        violations = scope_guard_violations(task_spec, self.temp_dir)

        self.assertIn(
            "README.md: staged edit outside task_spec.files_to_create_or_edit",
            violations,
        )

    def test_structured_budget_mapping_is_respected(self):
        task_spec = self.base_task_spec(
            {"max_added_lines": 180, "max_deleted_lines": 60, "forbid_rewrite": False}
        )
        self.stage_file("scripts/coder_execute.py", "line1\nline2\nline3\nadded\n")

        violations = scope_guard_violations(task_spec, self.temp_dir)

        self.assertEqual([], violations)
        self.assertEqual(
            {"scripts/coder_execute.py": {"added": 1, "deleted": 0}},
            collect_staged_diff_stats(self.temp_dir),
        )

    def test_parse_expected_diff_budget_from_string(self):
        budget = parse_expected_diff_budget("~2 inserted lines only, preserve/no-other-edits")

        self.assertEqual(2, budget["max_added_lines"])
        self.assertEqual(0, budget["max_deleted_lines"])
        self.assertTrue(budget["forbid_rewrite"])


if __name__ == "__main__":
    unittest.main()
