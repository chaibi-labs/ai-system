## Summary

<1-3 lines: what does this PR change at a behavioral level?>

## Linked issue

Closes #

## task_spec

<!-- Required for any PR opened by the coder agent. Paste the YAML or link. -->

```yaml
# task_spec here
```

## Tests

```
<command>
<actual output>
```

Pass count: X / Y

## Acceptance check

```
<command>
<actual output>
```

Result: pass | fail

## Risk

<low | medium | high> — <one-sentence reason>

## Cost flags

<none | <list>>

## Decisions needed from Anis

<none | <list>>

## Screenshots (UI only)

<!-- attach or describe -->

## Reviewer checklist

- [ ] Diff inside `task_spec.files_to_create_or_edit`
- [ ] Signatures match
- [ ] All `task_spec.test_files_and_cases` present
- [ ] No new deps outside `task_spec.allowed_new_dependencies`
- [ ] No `task_spec.out_of_scope` items snuck in
- [ ] Cost flags accurate
- [ ] No secrets committed
