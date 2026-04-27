import subprocess
from pathlib import Path

def run(cmd: list[str], cwd: Path | None = None, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=check, timeout=timeout)

def write_blocks(blocks: list[tuple[str, str]], repo_root: Path) -> list[str]:
    paths = []
    for file_path, content in blocks:
        full_path = repo_root / file_path
        with open(full_path, 'w') as f:
            f.write(content)
        paths.append(str(full_path))
    return paths

def has_staged_changes(repo_dir: Path) -> bool:
    result = run(['git', '-C', str(repo_dir), 'status', '--porcelain'])
    return len(result.stdout.strip()) > 0

def parse_expected_diff_budget(entry: object) -> dict[str, object]:
    if not isinstance(entry, dict):
        raise ValueError("Expected diff budget entry must be a dictionary")
    
    expected_keys = {'max_added_lines', 'max_deleted_lines', 'forbid_rewrite'}
    if any(key not in entry for key in expected_keys):
        raise KeyError(f"Missing one or more keys: {expected_keys}")
    
    return {
        "max_added_lines": int(entry['max_added_lines']),
        "max_deleted_lines": int(entry['max_deleted_lines']),
        "forbid_rewrite": bool(entry['forbid_rewrite'])
    }

def collect_staged_diff_stats(repo_dir: Path) -> dict[str, dict[str, int]]:
    result = run(['git', '-C', str(repo_dir), 'diff', '--cached', '--numstat'], text=True)
    stats = {'added': 0, 'deleted': 0}
    
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        added, deleted, _ = map(int, parts)
        stats['added'] += added
        stats['deleted'] += deleted
    
    return {'files_changed': {
        'total_added_lines': stats['added'],
        'total_deleted_lines': stats['deleted']
    }}

def scope_guard_violations(task_spec: dict, repo_dir: Path) -> list[str]:
    violations = []
    
    for entry in task_spec.get('expected_diff_shape', []):
        if isinstance(entry, dict) and 'scripts/coder_execute.py' in entry:
            budget = parse_expected_diff_budget(entry['scripts/coder_execute.py'])
            diff_stats = collect_staged_diff_stats(repo_dir)
            
            if budget['forbid_rewrite']:
                violations.append(f"Rewriting script/coder_execute.py is forbidden")
            
            if diff_stats['files_changed']['total_added_lines'] > budget['max_added_lines']:
                violations.append(f"Added lines ({diff_stats['files_changed']['total_added_lines']}) exceed max ({budget['max_added_lines']})")
            
            if diff_stats['files_changed']['total_deleted_lines'] > budget['max_deleted_lines']:
                violations.append(f"Deleted lines ({diff_stats['files_changed']['total_deleted_lines']}) exceed max ({budget['max_deleted_lines']})")
    
    return violations

def main() -> int:
    # Placeholder for actual main logic
    pass

if __name__ == "__main__":
    exit(main())
