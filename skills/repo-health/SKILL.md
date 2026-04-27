---
name: repo-health
description: 'Run scripts/repo_health.py to verify the ai-system repo has its expected layout — required folders, required files, no empty load-bearing files. Returns green / yellow (warnings) / red (missing files). NOT for product-repo health (separate skill if needed).'
metadata:
  openclaw:
    emoji: "🩺"
    requires:
      anyBins: ["python3"]
---

# /repo-health — Verify ai-system structure

Trigger: `/repo-health`

## What you do

```bash
[[ -f /home/anis/.ai-system/HALT ]] && { echo "HALTED"; exit 0; }
cd /home/anis/src/ai-system
git pull --ff-only
python3 scripts/repo_health.py
```

The script:
1. Walks the repo and confirms all required folders exist (agents, prompts, policies, workflows, scripts, templates, evaluations/{tasks,expected,reports}, decisions, memory, products, reports, skills, .github)
2. Confirms all required files exist (~40 files across the layout — full list in `scripts/repo_health.py`)
3. Flags any empty load-bearing files
4. Returns:
   - exit 0 + verdict `green`: everything in place
   - exit 1 + verdict `yellow`: empty load-bearing files (warning)
   - exit 2 + verdict `red`: missing dirs or files

## Output to user

Pretty-print the JSON result:

```
Verdict:        green | yellow | red
Missing dirs:   [<list>]
Missing files:  [<list>]
Empty files:    [<list>]
Checked at:     <timestamp>
```

If yellow or red, the next action is usually to open an issue with `agent:nightly` and `type:chore` labels noting the gaps, then a PR to `ai-system` with the missing files.
