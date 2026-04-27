# PR Template

## Summary

<1-3 lines: what does this PR change at a behavioral level? Not a list of files.>

## Linked issue

Closes #N

## task_spec

<!-- Paste the task_spec YAML here as a code block, or link to it.
     Required for any PR opened by the coder agent. -->

```yaml
task_spec:
  ...
```

## Tests

```
<command>
<actual output — paste, don't summarize>
```

Pass count: X / Y

## Acceptance check

```
<task_spec.acceptance_check.command>
<actual output>
```

Result: pass | fail

## Risk

<low | medium | high>

Why: <one or two sentences>

## Cost flags

<none | <list any new cost: paid SDK, hosted service, EAS build, etc.>>

## Decisions needed from Anis

<none | <bulleted list with specifics>>

## Screenshots (UI changes only)

<paste screenshots or describe visual change>

## Reviewer checklist (filled by reviewer agent)

- [ ] Diff stays within `task_spec.files_to_create_or_edit`
- [ ] Function signatures match `task_spec.function_signatures`
- [ ] All `task_spec.test_files_and_cases` are present
- [ ] No new dependencies outside `task_spec.allowed_new_dependencies`
- [ ] No `task_spec.out_of_scope` items snuck in
- [ ] Cost flags accurate
- [ ] No secrets committed
