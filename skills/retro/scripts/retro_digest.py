#!/usr/bin/env python3
"""Build a short, redacted digest of how the owner and Claude talked, from Claude Code transcripts.

It keeps only what a retro needs: the owner's own messages (typed, mid-turn, or button answers),
the questions Claude put to them (question cards, the next-step box, and questions in its replies),
interruptions, refused tool calls, and commands the owner ran themself. Tool output, file contents
and Claude's working are left out. Anything shaped like a secret, an email, a home path or an IP
address is blanked before it's printed.

    python3 -I retro_digest.py [--days N | --since YYYY-MM-DD] [--session ID_OR_PATH] [--project DIR]

Reads only. Prints Markdown to stdout.
"""
from __future__ import annotations

import argparse
import getpass
import datetime as dt
import glob
import json
import os
import re
import sys

# ---------- redaction ----------
_KV = re.compile(r"(?i)\b(pass(?:word|wd|phrase)?|secret|token|api[_-]?key|bearer|auth(?:orization)?)\b"
                 r"(\s*[:=]\s*\S+|\s+(?=\S*[\d!@#$%^&*])\S{6,})")
# After "password:" (or "=") the value is always blanked. After a plain space, only a word with a digit or
# symbol in it, six characters or longer, so "password in the tab" stays readable but "password hunter2x" doesn't.
_LONG = re.compile(r"[A-Za-z0-9+/_=.-]{24,}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_HOME = re.compile(r"/Users/[^/\s]+")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
try:
    _ACCOUNT = re.compile(re.escape(getpass.getuser()), re.I)
except Exception:  # no login name: nothing to blank
    _ACCOUNT = None


def _long_token(m: re.Match) -> str:
    s = m.group(0)
    # Paths, URLs and dotted names are words, not secrets: keep them when they read like text.
    if "/" in s or s.count(".") >= 2:
        return s
    has_digit = any(ch.isdigit() for ch in s)
    has_alpha = any(ch.isalpha() for ch in s)
    return "<redacted>" if has_digit and has_alpha else s


def redact(text: str) -> str:
    text = _HOME.sub("~", text)
    if _ACCOUNT is not None:
        text = _ACCOUNT.sub("<account>", text)
    text = _EMAIL.sub("<email>", text)
    text = _KV.sub(lambda m: m.group(1) + (": " if ":" in m.group(2) or "=" in m.group(2) else " ") + "<redacted>", text)
    text = _LONG.sub(_long_token, text)
    text = _IP.sub(lambda m: m.group(0) if m.group(0).startswith("127.") else "<ip>", text)
    return text


def clip(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


# ---------- reading ----------
NOT_OWNER = ("This session is being continued", "Another Claude session sent a message", "Base directory for this skill:",
             "[Usage limit", "[Earlier usage-limit", "[SYSTEM NOTIFICATION")


def project_dir(start: str) -> str | None:
    root = os.path.expanduser("~/.claude/projects")
    p = os.path.abspath(start)
    while True:
        cand = os.path.join(root, p.replace("/", "-"))
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def transcripts(args) -> list[str]:
    if args.session:
        s = os.path.expanduser(args.session)
        if os.path.isfile(s):
            return [s]
        d = project_dir(args.project)
        cands = glob.glob(os.path.join(d, s + "*.jsonl")) if d else []
        if not cands:
            sys.exit(f"retro_digest: no transcript for {args.session!r}")
        return cands
    d = project_dir(args.project)
    if not d:
        sys.exit(f"retro_digest: no transcript folder for {args.project} under ~/.claude/projects")
    return sorted(glob.glob(os.path.join(d, "*.jsonl")), key=os.path.getmtime)


def ts(o: dict) -> dt.datetime | None:
    t = o.get("timestamp")
    if not isinstance(t, str):
        return None
    try:
        return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def prose_questions(text: str) -> list[str]:
    out = []
    for para in text.split("\n"):
        para = para.strip().lstrip("-*> ").strip()
        if para.endswith("?") and 8 < len(para) < 400 and not para.startswith("```"):
            out.append(para)
    return out[-2:]


def _unique(items):
    seen, out = set(), []
    for a in items:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def digest(paths: list[str], since: dt.datetime) -> tuple[list[dict], dict, list]:
    """Pair each message from the owner with the questions Claude asked since the owner last spoke.

    Questions stay open across shell commands, interruptions and refusals, and attach to the next
    real reply: typed, a card answer, or a message sent mid-turn. Identical repeats are shown once.
    """
    ex: list[dict] = []
    stats = dict(sessions=0, owner=0, midturn=0, short_yes=0, asked_cards=0, asked_box=0, replaced=0,
                 asked_prose=0, interrupts=0, refused=0, owner_shell=0, pasted=0)
    still_open: list = []
    for path in paths:
        pending: list[tuple[str, str]] = []
        last_text_qs: list[str] = []
        used = False
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                when = ts(o)
                if when is None or when < since or o.get("isSidechain"):
                    continue
                t = o.get("type")
                m = o.get("message") if isinstance(o.get("message"), dict) else {}
                c = m.get("content")
                text, kind = None, None
                if t == "assistant" and isinstance(c, list):
                    for b in c:
                        if b.get("type") == "text":
                            last_text_qs = prose_questions(b.get("text", ""))
                        elif b.get("type") == "tool_use":
                            name, inp = b.get("name", ""), b.get("input") or {}
                            if name == "AskUserQuestion":
                                pending += [("card", q.get("question", "")) for q in inp.get("questions") or []]
                            elif name.endswith("__wrap_up") and inp.get("ask"):
                                pending.append(("box", inp["ask"]))
                    continue
                if t == "user":
                    if isinstance(c, str):
                        s = c.lstrip()
                        if s.startswith("<bash-input>"):
                            stats["owner_shell"] += 1
                            text, kind = "(ran a shell command themself)", "shell"
                        elif s.startswith("<") or s.startswith(NOT_OWNER):
                            continue
                        else:
                            text, kind = c, "typed"
                    elif isinstance(c, list):
                        for b in c:
                            if b.get("type") == "text" and b.get("text", "").startswith("[Request interrupted"):
                                stats["interrupts"] += 1
                                text, kind = "(interrupted Claude)", "interrupt"
                            elif b.get("type") == "tool_result":
                                body = b.get("content")
                                body = body if isinstance(body, str) else json.dumps(body)
                                # Only the harness's own refusal, which opens the result; a tool's output that merely
                                # mentions the phrase (a test file, a log) isn't a refusal.
                                if body.lstrip().lstrip('"[{').lstrip().startswith(("The user doesn't want to proceed", "User rejected")):
                                    stats["refused"] += 1
                                    text, kind = "(refused a tool call)", "refused"
                        r = o.get("toolUseResult")
                        if isinstance(r, dict) and isinstance(r.get("answers"), dict) and r["answers"]:
                            text = "; ".join(f"{k} → {v}" for k, v in r["answers"].items())
                            kind = "card answer"
                elif t == "attachment":
                    a = o.get("attachment") or {}
                    if a.get("type") == "queued_command" and a.get("humanTurn") and isinstance(a.get("prompt"), str):
                        stats["midturn"] += 1
                        text, kind = a["prompt"], "mid-turn"
                if text is None:
                    continue
                used = True
                if kind in ("shell", "interrupt", "refused"):
                    # Not an answer: whatever was asked stays open for the next real reply.
                    ex.append(dict(when=when, kind=kind, text=text, asked=[]))
                    continue
                stats["owner"] += 1
                asked = _unique(pending)
                if not asked and kind == "typed":
                    asked = [("prose", q) for q in last_text_qs]
                for k in ("card", "box", "prose"):
                    stats["asked_" + {"card": "cards", "box": "box", "prose": "prose"}[k]] += sum(1 for x, _ in asked if x == k)
                stats["replaced"] += max(0, sum(1 for x, _ in asked if x == "box") - 1)
                if kind == "typed" and text.count("\n") >= 4:
                    kind = "typed, several lines: may be pasted output"
                    stats["pasted"] += 1
                ex.append(dict(when=when, kind=kind, text=text, asked=asked))
                pending, last_text_qs = [], []
        if pending:
            still_open += _unique(pending)
        stats["sessions"] += 1 if used else 0
    for e in ex:
        s = e["text"].strip()
        if e["kind"] == "typed" and len(s) < 40 and re.match(r"(?i)^(yes|no|ok|okay|sure|done|go|great|thanks?)\b", s):
            stats["short_yes"] += 1
            e["short"] = True
    ex.sort(key=lambda e: e["when"])
    return ex, stats, still_open


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--days", type=float, default=1.0, help="look back this many days (default 1)")
    g.add_argument("--since", help="start date, YYYY-MM-DD (UTC)")
    ap.add_argument("--session", help="one session: its id (or the start of it) or a .jsonl path")
    ap.add_argument("--project", default=os.getcwd(), help="the project folder whose transcripts to read (default: here)")
    ap.add_argument("--width", type=int, default=400, help="longest message kept, in characters (default 400)")
    args = ap.parse_args(argv)
    now = dt.datetime.now(dt.timezone.utc)
    since = (dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc) if args.since
             else now - dt.timedelta(days=args.days))
    ex, st, still_open = digest(transcripts(args), since)
    local = dt.datetime.now().astimezone().tzinfo

    def stamp(w: dt.datetime) -> str:
        return f"{w:%m-%d %H:%M} UTC ({w.astimezone(local):%a %H:%M} local)"

    print(f"# Retro digest\n\nFrom {since:%Y-%m-%d %H:%M} UTC to {now:%Y-%m-%d %H:%M} UTC, {st['sessions']} session(s); "
          f"local time is {dt.datetime.now().astimezone():%Z (UTC%z)}. Redacted: secret-shaped strings, emails, home paths, "
          "IP addresses and the account name.\n")
    print("| Count | What |\n|---|---|")
    for k, label in [("owner", "messages from the owner (typed, mid-turn or card answers)"),
                     ("midturn", "of them sent while Claude was working"),
                     ("short_yes", "short yes / no / done replies"),
                     ("asked_box", "distinct next-step box questions before a reply"),
                     ("replaced", "box questions replaced by a newer one before the owner answered"),
                     ("asked_cards", "question cards"), ("asked_prose", "questions asked in Claude's replies"),
                     ("pasted", "messages of several lines (may be pasted output, not the owner's wording)"),
                     ("interrupts", "interruptions"), ("refused", "tool calls the owner refused"),
                     ("owner_shell", "shell commands the owner ran themself")]:
        print(f"| {st[k]} | {label} |")
    print("\nQuestions attach to the next real reply; shell commands, interruptions and refusals don't close them.\n")
    print("## Exchanges, oldest first\n")
    for e in ex:
        tag = e["kind"] + (", short" if e.get("short") else "")
        print(f"**{stamp(e['when'])}** ({tag})")
        for k, q in e["asked"]:
            print(f"- Claude asked ({k}): {clip(redact(q), 240)}")
        print(f"- Owner: {clip(redact(e['text']), args.width)}\n")
    if still_open:
        print("## Still unanswered when the window ended\n")
        for k, q in still_open:
            print(f"- ({k}) {clip(redact(q), 240)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
