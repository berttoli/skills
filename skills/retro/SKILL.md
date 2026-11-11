---
name: retro
description: A look back at how the user and Claude have been working together, built from a redacted digest of recent Claude Code sessions. It finds what cost round trips (questions asked twice, corrections, choices that needed a second message, approvals that could have been batched, unclear asks), gives two or three plain tips for each side, and saves the lessons to memory so they stick. Use it whenever the user types /retro, asks how to work better together, how to talk to Claude more effectively, wants feedback on their prompting or chat style, asks what slowed things down, or wants a look back at a session, a day or a week, even if they never say "retro".
---

# Retro

The point is fewer avoidable round trips, and lessons that come from what actually happened rather than from guesses. A round trip is avoidable when one side could have prevented it: Claude asked something it already knew, asked badly, or split one decision into several; or the user's wording left a real ambiguity. A question that was genuinely the user's to answer (a push, a deletion, credentials, money, anything irreversible) is never waste, so don't count it against anyone.

Be candid and specific. The user asked for this to get better, not to be reassured, so skip praise padding. If things are already working, say so in one line and don't invent changes.

## 1. Choose the window

Default to the last 24 hours in this project. If the user names a session, a day or a week, use that instead, and say which window you used at the top of the report.

## 2. Build the digest

Run, from the project's folder:

```bash
python3 -I <this skill's folder>/scripts/retro_digest.py --days 1
```

Options: `--days N`, `--since YYYY-MM-DD`, `--session <id or .jsonl path>`, `--project <folder>` (when the transcripts belong to another folder), `--width N` (longest message kept, 400 by default).

It prints Markdown:
- **Counts.** These include how many box questions were replaced by a newer one before the user answered, which is often the biggest avoidable cost.
- **Every user message in order,** stamped in UTC and the user's local time. Each comes with the questions Claude asked since the user last spoke.
  - A question stays open across shell commands, interruptions and refusals, and attaches to the next real reply, including one sent mid-turn.
  - A message of several lines is marked as possibly pasted output, so don't read it as the user's own wording.
- **Questions still unanswered when the window ended.**

It blanks secret-shaped strings, emails, home paths, IP addresses and the account name.

The digest holds the user's words and Claude's questions, not Claude's replies. To judge whether Claude followed through on something, use the project's own log if it keeps one.

Work from the digest, not the raw transcripts. Transcripts hold tool output, file contents and sometimes secrets; the digest exists so a retro never needs to open them. Keep the digest in the scratchpad (or another temp folder), never in a repo. If the project keeps its own log, you may read its entries for the same window for context; search it rather than reading it whole.

## 3. Read what's already known

Before judging anything, read the memory index and every memory about how Claude asks, approves, reports or batches. Some are `feedback` and some are `project` memories: the field may sit under `metadata:`, so read the index rather than grepping for `type:`. If the project keeps a practices list, read it too. Two reasons:
- You shouldn't save a lesson twice.
- **A saved rule that was broken again is the most useful finding there is:** it means the rule isn't working as written.

## 4. Find what cost round trips

Go through the exchanges and look for:

1. **Asked twice.** Claude asked something already answered, earlier in the window or in memory.
2. **Corrections.** The user had to correct Claude, restate something, or say "no, I meant…".
3. **A question that needed a second message.** Two decisions in one question, options that didn't fit, missing context so the user asked back, or jargon the user had to decode.
4. **Approvals one at a time.** Several related yes/no questions in a row that could have been one. Watch also for a question re-asked with a new count or wording but no reply in between.
5. **Displaced or skipped questions.** When two or more questions are listed before one reply, the earlier ones were replaced before the user could answer. That cost is Claude's, and the user may have answered the older question, not the newest. Call a question skipped only if it was still the one showing when the user replied with something else.
6. **Mid-turn messages.** Note what each was: a new task, a correction or an add-on. They're normally fine; flag only ones Claude mishandled.
7. **User-side wording that forced a question:**
   - an unclear "it" or "that";
   - a slip that flipped the meaning, such as "if it does" for "if it doesn't";
   - a request without its reason;
   - a decision made in another session that Claude then had to find.
8. **What worked,** so it's kept: patterns that got a decision in one message.

For each finding, keep the evidence: the time, and the words, quoted exactly and briefly (no more than about 15 words). The words can be the user's, or Claude's own question when the cost was Claude's. Never quote anything that was redacted or looks like a secret. Estimate the round trips each cost when you can, and leave out time the user spent on steps only they could do, such as sign-ins and passwords.

## 5. Report

Write it in plain language. The user may read it on a phone, so keep it short and free of jargon. Give times in the user's local time, which the digest shows next to UTC. Use this shape:

```markdown
# Retro: <window>

**In short:** <two sentences: the biggest cost, and the one change that would help most>

## What cost us round trips
- **<what happened>** (<time>, "<their words>"): <what it cost>. <Who could prevent it, and how.>

## For you
1–3 tips, each tied to a real exchange above.

## For me
1–3 changes Claude will make, each tied to a real exchange above.

## What's working
1–3 things to keep.

## Saved
What went into memory or the practices list, by name.
```

If the window had too few exchanges to say anything useful, say so and stop. Don't stretch thin evidence into tips.

## 6. Save the lessons

- **Changes in Claude's own behaviour** go into feedback memories, one fact per file, each with **Why** and **How to apply**. Update an existing memory rather than adding a near-duplicate. Save only lessons backed by at least one real exchange.
- **How to read this user** can be saved when it changes how Claude interprets them, for example a phrasing they use with a particular meaning. Tips for the user are advice, not rules about them, so don't save those as memories.
- **A practices list,** if the project keeps one: add new real cases in its own format and numbering.
- **A project log,** if there is one: add one short entry saying the retro ran and what was saved, following that log's own rules (anchors, append-only, and so on). The newest entries aren't always at the end of the file, so find where they actually are before inserting.
- **Change nothing else:** no settings, CLAUDE.md, permissions or code, and no pushing. The retro reads and reports; the only writes are memory, the practices list and the log entry.
- **Running as a subagent?** File writes may be refused. Return the report and each proposed note as text, and let the main session save them.
