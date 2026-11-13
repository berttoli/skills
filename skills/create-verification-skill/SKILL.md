---
name: create-verification-skill
description: "Generate and exercise a project-local Codex or Claude verification skill for real UI, CLI, or service behavior. Use when asked to create a verification/control skill or repeatable app verification procedure."
disable-model-invocation: true
---

# Create a verification skill

A verification skill drives the real app and proves behavior: launch it, exercise a feature the way a user would, and capture evidence. Generate a project-local skill tailored to the repo. Write it for the next agent, who may read it cold without prior knowledge of the app.

## Choose the project skill location

Honor the requested agent and the repository's existing skill layout. Otherwise:

- **Codex:** use `.agents/skills/verify-<app>/`.
- **Claude Code:** use `.claude/skills/verify-<app>/`.
- **Both:** keep one source at `.agents/skills/verify-<app>/` and expose it through a relative symlink at `.claude/skills/verify-<app>` pointing to `../../.agents/skills/verify-<app>`. Resolve and check the link from its containing directory. If the repository does not support symlinks, follow its existing sync convention and verify both copies match.

Use this chosen directory as `<skill-dir>` below. Read existing files or links before changing them; preserve unrelated content and never replace a conflicting skill silently. Keep project-specific commands and data in the project, not in the shared generator. Use tools available in the active agent; do not assume a Cursor-only tool or a particular browser integration exists.

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI/TUI, a desktop app, an API, a mobile app, a library? A repo can have several; pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented dev command (package scripts, Makefile, README quickstart). Note ports, env vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically? Existing harnesses first — Playwright/Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port. Only then pick a generic recipe: browser/CDP for web and Electron, a tmux/PTY harness for CLI/TUI, plain HTTP for services.
- **Observe:** what evidence can be captured? Screenshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, say so in the generated skill: refusing to double-drive a shared instance beats corrupting the user's session.

If the checkout doesn't build or start as-is, fix that within the authorized scope or report the blocker before claiming a verified result. A skill written against a broken base teaches wrong steps. When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, clearly marked as verification scaffolding, and remove only that scaffolding in cleanup. Prefer an isolated local or test instance; driving a workflow does not authorize production mutations, external messages, or publishing evidence.

## 2. Generate the skill

Write `<skill-dir>/SKILL.md` with YAML frontmatter (`name: verify-<app>` and a `description` that names the app, the surface, and when to reach for it) and these sections, each grounded in what the interview actually found (no placeholders left):

- **Launch:** the exact command that starts the app for verification, and how to tell it's ready (a log line, a prompt). Launch must reach a usable state from an empty data dir, including any migrations and seed data. Ready means usable, not just that a process answers. A database health check can pass while its init scripts are still running. Include teardown. For a short-lived CLI or TUI there is no server to keep alive: launch means build the binary (or install deps) once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" — process up, right version/build, port owned by us, auth valid. An agent runs this first whenever anything looks off.
- **Drive:** the harness recipe with real selectors/commands from this repo, not examples. Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes. State the proof standards: exercise the real user path, not internal setters or test-only endpoints; capture the action and the resulting state, not just the final screen; verify side effects (files written, rows inserted, messages sent) alongside what's visible; mocks only where a production boundary already isolates the external system. When the safe path is a dry-run or test mode, verify what it actually skips by observing (files, network, git refs) rather than trusting its name: some dry-runs still touch the network or open a browser.
- **Cleanup:** how to tear down instances the run created. Never kill by process name; kill what you started. Cleanup removes instances and scratch state, never the evidence: proof artifacts survive the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill body. A helper the reader has to reverse-engineer is not a helper.

## 3. Seed the feature map

Create `<skill-dir>/features/README.md` plus one file per user-facing feature you can identify (aim for the top 3-5 to start, from routes, commands, menus, or docs). Follow the shape in [`references/feature-map-example/README.md`](references/feature-map-example/README.md), with a README index and one file per feature. The Notes app and `control-notes` commands in that example are illustrative; discover the actual app's interfaces and do not install or invent those example tools. Each file answers, from the user's point of view: what the feature is, how to reach it, how to drive it with the harness, and what observable end state proves it works. The four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`. If the seed data lacks a precondition that a journey needs, the journey reports a failure and the reason goes in that feature's `Gotchas`. Never weaken the journey to make it pass. The map is the repo's maintained verification source; a proof that drives one convenient entry point is incomplete when the map lists others.

## 4. Prove the generated skill before handing it over

Run its own instructions end to end once: launch, doctor, drive ONE mapped feature (one is enough; the map exists so later runs can cover the rest), capture evidence, clean up. After cleanup, confirm the evidence still exists at the named location — a cleanup that eats the proof fails this step. Fix what fails, and run the generated cleanup after every failed iteration too, so broken attempts don't strand processes and ports. A generated skill that was never executed is a draft, not a deliverable. If you proved it in a stand-in for the real target (a container in place of a fresh VM, a local stack in place of a remote one), list every setup step the stand-in did that the target will not. Those steps stay unverified until a run on the real target covers them.

## 5. Offer the maintenance loop

When the app changes, revisit the affected feature entries, update their real commands and observable results, and rerun those journeys. Record which entry points passed, failed, or could not run, along with the evidence location. This maintenance procedure is self-contained; no companion skill is required. Suggest a cadence only if asked.
