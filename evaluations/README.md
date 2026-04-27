# Evaluations — Regression Suite

This is the falsifiability layer for the studio. Without it:

- Local model swaps cannot be compared
- Prompt changes cannot be validated as improvements
- Nightly self-improvement PRs to `ai-system` (level v3+) become a slow-motion regression engine

## Layout

```
evaluations/
├── tasks/                  # task_specs to run (in plan §12.5 format)
├── expected/               # expected outcomes per task
├── reports/                # historical run reports
├── fixtures/               # (auto-created) clean per-task working dirs
└── run_evals.py            # the harness
```

## Per-eval contract

Each `tasks/<NN>_<name>.yaml` is a real task_spec. Each `expected/<NN>_expected.json` is the verdict the harness should observe when the local executor implements the spec correctly.

```json
{
  "files_created":  ["..."],
  "files_modified": ["..."],
  "tests_added":    ["..."],
  "acceptance":     "pass",
  "diff_lines_max": 120
}
```

## Running

```
python3 evaluations/run_evals.py            # all tasks, default model
python3 evaluations/run_evals.py --task 01  # one task
python3 evaluations/run_evals.py --model qwen2.5-coder:7b   # try an alternative model
```

The harness writes `reports/<date>-<commit>.md` summarizing pass/fail, attempts used, codex calls used, wall clock per task.

## Regression gates

- **Local model swap:** must pass ≥80% of evals before being trusted as the executor.
- **Prompt change in `prompts/`:** re-run evals; merging requires no regression.
- **Nightly v3+ ai-system PRs:** CI runs the harness; PR cannot merge if the pass rate drops vs the current `main` baseline.

## Adding a new eval

When a real task fails in production in a way the suite should have caught, add a corresponding eval. Number it sequentially. Goal: cover the *kind* of failure, not the exact incident.
