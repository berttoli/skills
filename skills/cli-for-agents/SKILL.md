---
name: cli-for-agents
description: >-
  Designs or reviews CLIs so coding agents can run them reliably: non-interactive
  flags, layered --help with examples, stdin/pipelines, fast actionable errors,
  idempotency, dry-run, and predictable structure. Use when building a CLI,
  adding commands, writing --help, or improving a CLI for unattended automation.
---

# CLI for agents

Human-oriented CLIs often block agents: interactive prompts, huge upfront docs, and help text without copy-pasteable examples. Prefer patterns that work headlessly and compose in pipelines.

## Non-interactive first

- Every input should be expressible as a flag or flag value. Do not require arrow keys, menus, or timed prompts.
- If required flags are missing, fail with an actionable error. Offer an interactive fallback only when stdin is a terminal and the user chose interactive use; never hang a headless caller waiting for input.

**Bad:** `mycli deploy` → `? Which environment? (use arrow keys)`

**Good:** `mycli deploy --env staging`

## Discoverability without dumping context

- Agents discover subcommands incrementally: `mycli`, then `mycli deploy --help`. Do not print the entire manual on every run.
- Let each subcommand own its documentation so unused commands stay out of context.

## `--help` that works

- Every subcommand has `--help`.
- Every `--help` includes **Examples** with real invocations. Examples do more than prose for pattern-matching.

```text
Options:
  --env     Target environment (staging, production)
  --tag     Image tag (default: latest)
  --force   Skip confirmation

Examples:
  mycli deploy --env staging
  mycli deploy --env production --tag v1.2.3
  mycli deploy --env staging --force
```

## stdin, flags, and pipelines

- Accept stdin where it makes sense (e.g. `cat config.json | mycli config import --stdin`).
- Avoid odd positional ordering and avoid falling back to interactive prompts for missing values.
- Support chaining: `mycli deploy --env staging --tag $(mycli build --output tag-only)`.

## Fail fast with actionable errors

- On missing required flags: exit immediately with a clear message and a **correct example invocation**, not a hang.

```text
Error: No image tag specified.
  mycli deploy --env staging --tag <image-tag>
  Available tags: mycli build list --output tags
```

## Idempotency

- Agents retry often. Make retries safe with a stable operation ID, an idempotency key, or an explicit "already done" result. For commands that intentionally create a new object each time, document that behavior and provide a way to identify or reconcile a previous attempt before retrying.

## Destructive actions

- Add `--dry-run` (or equivalent) so agents can preview plans before committing.
- Offer `--yes` / `--force` to skip confirmations while keeping the safe default for humans.
- A confirmation flag does not grant authorization or bypass access checks. Define which side effects a dry run avoids, and verify that claim against files, network calls, or remote state as relevant.

## Predictable structure

- Use a consistent pattern everywhere, e.g. `resource` + `verb`: if `mycli service list` exists, `mycli deploy list` and `mycli config list` should follow the same shape.

## Success output

- On success, return machine-useful data: IDs, URLs, durations. Plain text is fine; avoid relying on decorative output alone.
- Keep result data on stdout and diagnostics on stderr. Where structured output is offered, keep its schema predictable and pair failures with a nonzero exit code.

```text
deployed v1.2.3 to staging
url: https://staging.myapp.com
deploy_id: dep_abc123
duration: 34s
```

## When reviewing an existing CLI

- Check: non-interactive path, layered help, examples on `--help`, stdin/pipeline story, error messages with invocations, idempotency, dry-run, confirmation bypass flags, consistent command structure, structured success output.
