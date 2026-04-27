# Coder Executor Prompt

This document outlines the behavior of the Coder Executor. The executor is responsible for generating code based on a given task specification and fixture files.

## Behavior Rules

1. **Separate Test Function per Task Case**: Each test case in `task_spec.test_files_and_cases` should have its own separate test function.
2. **Explicit Imports**: All referenced symbols from the fixture file tree, including those from `src/strings.py`, must be explicitly imported. For example:
   ```python
   from src.strings import slugify
   ```

## Example

Given a task specification with multiple test cases, the executor should generate separate test functions for each case and include the necessary imports.

### Task Specification
```json
{
  "issue": "#1 Fix executor – eval 02 missing import + folded 5 test cases into 1",
  "target_branch_name": "fix/executor-eval-02-test-generation-prompt",
  "files_to_create_or_edit": [
    "evaluations/run_evals.py",
    "prompts/coder-executor.md"
  ],
  "function_signatures": [
    {
      "file": "evaluations/run_evals.py",
      "exports": [
        "def build_executor_prompt(task_spec: dict, fixture_dir: Path) -> str:"
      ]
    }
  ],
  "expected_diff_shape": [
    {
      "evaluations/run_evals.py": "modified (~10-20 lines, add explicit eval-mode implementation rules requiring one separate test function per task_spec.test_files_and_cases case and imports for referenced symbols using the fixture file tree, including src/strings.py -> from src.strings import slugify guidance)"
    },
    {
      "prompts/coder-executor.md": "modified (~5-15 lines, add parallel production executor behavior rules requiring one separate test function per case and explicit imports for referenced existing symbols)"
    }
  ],
  "test_files_and_cases": [],
  "acceptance_check": {
    "command": "python3 evaluations/run_evals.py --task 01 --model qwen2.5-coder:14b && python3 evaluations/run_evals.py --task 02 --model qwen2.5-coder:14b",
    "expected": "exit code 0; eval 01 verdict pass; eval 02 verdict pass; with the configured real model available, eval 02 acceptance output shows python3 -m pytest -q exits 0 with 5 passed"
  },
  "out_of_scope": [
    "changes to eval tasks other than prompt instructions for task 02 behavior",
    "fixes for eval failures 03, 04, or 05",
    "executor runtime or tool-loop refactors",
    "model changes, model downloads, or paid API usage",
    "adding, removing, or changing dependencies",
    "changing fixture source code or expected acceptance semantics",
    "weakening file-scope, dependency, BLOCKED, or output-format rules"
  ],
  "allowed_new_dependencies": {
    "npm": [],
    "pip": [],
    "apt": []
  },
  "budget": {
    "max_executor_attempts": 3,
    "max_codex_calls": 6,
    "wall_clock_hours": 2,
    "max_plan_execute_cycles": 2,
    "heartbeat_interval_minutes": 10
  }
}
```

### Generated Code

```python
from pathlib import Path
from src.strings import slugify

def build_executor_prompt(task_spec: dict, fixture_dir: Path) -> str:
    # Your implementation here
    pass
```

