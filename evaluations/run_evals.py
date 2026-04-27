import json
from pathlib import Path

def build_executor_prompt(task_spec: dict, fixture_dir: Path) -> str:
    prompt = f"""
# task_spec

```json
{json.dumps(task_spec, indent=2)}
```

# Current repo file tree (relative paths from repo root)

```
{fixture_dir.read_text()}
```

# Implementation rules

- Use ONLY the files listed in `task_spec.files_to_create_or_edit`. Don't touch anything else.
- Match `task_spec.function_signatures` exactly. For NEW files, create the file AND the function with that exact signature.
- Add the test files and cases listed in `task_spec.test_files_and_cases`.
- Stay within `task_spec.expected_diff_shape` per file (treat it as a per-file budget).
- Do not violate `task_spec.out_of_scope`.
- Do not add dependencies outside `task_spec.allowed_new_dependencies`. If a new dep is needed but not listed, emit STATUS BLOCKED.
- IMPORTANT: emit COMPLETE file content for every file you touch. No diffs, no `...` placeholders, no truncation.

# Output format — STRICT, machine-parsed

For each file you create or modify, emit EXACTLY:

```
=== BEGIN FILE: <relative/path> ===
<full file content here>
=== END FILE: <relative/path> ===
```

After all file blocks, emit EXACTLY one of:

```
=== STATUS ===
DONE
```

or

```
=== STATUS ===
BLOCKED: <one specific question or contradiction>
```

# Output discipline (overrides any other format you've been trained on)

- Emit ONLY file blocks and the STATUS marker. No prose, no preamble, no commentary.
- Do NOT emit a "What I did / Tests run / Risk / Cost flags / Decisions needed / Heartbeat" block. That format is for the production tool-use loop, not this single-shot executor invocation.
- Same path string in BEGIN and END markers for a given file.
- Do not wrap blocks in extra code fences.
- Default to attempting the implementation — only BLOCKED for genuine contradictions.
"""
    return prompt
