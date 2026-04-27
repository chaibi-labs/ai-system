import unittest
from pathlib import Path
import tempfile
import shutil
from subprocess import run as run_subprocess
from scripts.coder_execute import scope_guard_violations, parse_expected_diff_budget, collect_staged_diff_stats

class TestCoderExecuteScopeGuard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        run_subprocess(['git', '-C', self.temp_dir, 'init'])
        with open(Path(self.temp_dir) / 'README.md', 'w') as f:
            f.write("Initial commit")
        run_subprocess(['git', '-C', self.temp_dir, 'add', '.'])
        run_subprocess(['git', '-C', self.temp_dir, 'commit', '-m', 'Initial commit'])

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_over_budget_rewrite_is_blocked(self):
        task_spec = {
            "expected_diff_shape": [
                {
                    "scripts/coder_execute.py": "~2 inserted lines only, preserve/no-other-edits language, and many deletions"
                }
            ]
        }

        run_subprocess(['git', '-C', self.temp_dir, 'checkout', '--orphan', 'new_branch'])
        run_subprocess(['git', '-C', self.temp_dir, 'add', '.'])
        
        violations = scope_guard_violations(task_spec, Path(self.temp_dir))
        self.assertIn("Rewriting script/coder_execute.py is forbidden", violations)

    def test_within_budget_insertion_is_allowed(self):
        task_spec = {
            "expected_diff_shape": [
                {
                    "scripts/coder_execute.py": "~180 added lines, ~60 deleted lines max"
                }
            ]
        }

        run_subprocess(['git', '-C', self.temp_dir, 'checkout', '--orphan', 'new_branch'])
        with open(Path(self.temp_dir) / 'scripts/coder_execute.py', 'w') as f:
            f.write("New content" * 180)
        run_subprocess(['git', '-C', self.temp_dir, 'add', '.'])

        violations = scope_guard_violations(task_spec, Path(self.temp_dir))
        self.assertEqual(violations, [])

    def test_staged_edits_to_a_file_outside_task_spec_are_blocked(self):
        task_spec = {
            "expected_diff_shape": [
                {
                    "scripts/coder_execute.py": "~180 added lines, ~60 deleted lines max"
                }
            ]
        }

        run_subprocess(['git', '-C', self.temp_dir, 'checkout', '--orphan', 'new_branch'])
        with open(Path(self.temp_dir) / 'new_file.txt', 'w') as f:
            f.write("Some content")
        run_subprocess(['git', '-C', self.temp_dir, 'add', '.'])

        violations = scope_guard_violations(task_spec, Path(self.temp_dir))
        self.assertIn("Rewriting script/coder_execute.py is forbidden", violations)

    def test_structured_budget_mapping_is_respected(self):
        task_spec = {
            "expected_diff_shape": [
                {
                    "scripts/coder_execute.py": {
                        "max_added_lines": 180,
                        "max_deleted_lines": 60,
                        "forbid_rewrite": False
                    }
                }
            ]
        }

        run_subprocess(['git', '-C', self.temp_dir, 'checkout', '--orphan', 'new_branch'])
        with open(Path(self.temp_dir) / 'scripts/coder_execute.py', 'w') as f:
            f.write("New content" * 180)
        run_subprocess(['git', '-C', self.temp_dir, 'add', '.'])

        violations = scope_guard_violations(task_spec, Path(self.temp_dir))
        self.assertEqual(violations, [])

if __name__ == "__main__":
    unittest.main()
