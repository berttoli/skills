#!/usr/bin/env python3
"""Tests for retro_digest.py on made-up transcripts. Run: python3 -I test_retro_digest.py"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retro_digest as rd  # noqa: E402

T0 = "2026-11-11T07:00:00Z"


def at(minute: int) -> str:
    return f"2026-11-11T07:{minute:02d}:00Z"


def user(text, minute, **kw):
    o = dict(type="user", timestamp=at(minute), message=dict(role="user", content=text))
    o.update(kw)
    return o


def assistant(blocks, minute):
    return dict(type="assistant", timestamp=at(minute), message=dict(role="assistant", content=blocks))


ACCOUNT = __import__("getpass").getuser()
FAKE_KEY = "sk" + "-live-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"  # built in pieces so no scanner mistakes it for a real one
LINES = [
    user("old message before the window", 0, timestamp="2026-11-01T00:00:00Z"),
    user("deploy it, my email is someone@example.com and the key is " + FAKE_KEY + " in /Users/somebody/code", 1),
    assistant([{"type": "text", "text": "Done.\n\nShould I also push it?"}], 2),
    user("no, never push without asking", 3),
    assistant([{"type": "tool_use", "id": "w1", "name": "mcp__ccd_turn__wrap_up", "input": {"recap": "r", "ask": "Trash the 3 old logs?"}}], 4),
    user("Yes, trash them", 5),
    assistant([{"type": "tool_use", "id": "q1", "name": "AskUserQuestion", "input": {"questions": [{"question": "Which port range?"}]}}], 6),
    dict(type="user", timestamp=at(7), message=dict(role="user", content=[{"type": "tool_result", "tool_use_id": "q1", "content": "ok"}]),
         toolUseResult={"questions": [], "answers": {"Which port range?": "5300-5399"}}),
    dict(type="attachment", timestamp=at(8), attachment=dict(type="queued_command", humanTurn=True, prompt="also, password: hunter2xyz")),
    dict(type="user", timestamp=at(9), message=dict(role="user", content=[{"type": "text", "text": "[Request interrupted by user]"}])),
    user("<bash-input>sudo something</bash-input>", 10),
    user("Another Claude session sent a message: <cross-session-message>hi</cross-session-message>", 11),
    user("This session is being continued from a previous conversation...", 12),
    user("<task-notification>done</task-notification>", 13),
    user("sidechain words", 14, isSidechain=True),
    dict(type="user", timestamp=at(15), message=dict(role="user", content=[{"type": "tool_result", "tool_use_id": "x", "content": "The user doesn't want to proceed with this tool use."}])),
    user("server at 192.168.1.20 and 127.0.0.1:8080", 16),
    user("[Usage limit reached; a short grace allowance remains]", 17),
    assistant([{"type": "tool_use", "id": "w2", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Same question?"}}], 18),
    assistant([{"type": "tool_use", "id": "w3", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Same question?"}}], 19),
    user("my login is " + ACCOUNT + " on this Mac", 20),
    assistant([{"type": "tool_use", "id": "w4", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Create the bucket?"}}], 21),
    user("<bash-input>gcloud auth login</bash-input>", 22),
    user("Yes, create it", 23),
    assistant([{"type": "tool_use", "id": "w5", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "First decision?"}}], 24),
    assistant([{"type": "tool_use", "id": "w6", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Second decision?"}}], 25),
    user("When needed", 26),
    assistant([{"type": "tool_use", "id": "w7", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Is it switched on?"}}], 27),
    dict(type="attachment", timestamp=at(28), attachment=dict(type="queued_command", humanTurn=True, prompt="It's off")),
    user("the password in the test tab, the passphrase is needed, password hunter2x", 29),
    user("line one\nline two\nline three\nline four\nline five", 30),
    assistant([{"type": "tool_use", "id": "w8", "name": "mcp__ccd_turn__wrap_up", "input": {"ask": "Left hanging?"}}], 31),
]


class DigestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.path = os.path.join(cls.dir, "s1.jsonl")
        with open(cls.path, "w", encoding="utf-8") as f:
            for o in LINES:
                f.write(json.dumps(o) + "\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rd.main(["--session", cls.path, "--since", "2026-11-11"])
        cls.out = buf.getvalue()

    def test_secrets_emails_paths_and_ips_are_blanked(self):
        for leaked in (FAKE_KEY, "someone@example.com", "/Users/somebody", "hunter2xyz", "192.168.1.20"):
            self.assertNotIn(leaked, self.out)
        self.assertIn("<email>", self.out)
        self.assertIn("~/code", self.out)
        self.assertIn("127.0.0.1:8080", self.out)

    def test_only_the_owners_words_are_kept(self):
        self.assertNotIn(ACCOUNT, self.out)
        self.assertIn("my login is <account> on this Mac", self.out)
        self.assertEqual(self.out.count("Claude asked (box): Same question?"), 1)
        for gone in ("Usage limit", "old message before the window", "cross-session", "being continued", "task-notification", "sidechain words"):
            self.assertNotIn(gone, self.out)

    def test_questions_are_paired_with_answers(self):
        self.assertIn("Claude asked (prose): Should I also push it?", self.out)
        self.assertIn("Claude asked (box): Trash the 3 old logs?", self.out)
        self.assertIn("Claude asked (card): Which port range?", self.out)
        self.assertIn("Which port range? → 5300-5399", self.out)

    def test_counts(self):
        rows = {line.split("|")[2].strip(): int(line.split("|")[1]) for line in self.out.splitlines() if line.startswith("| ") and line.split("|")[1].strip().isdigit()}
        self.assertEqual(rows["messages from the owner (typed, mid-turn or card answers)"], 12)  # 9 typed + 1 card answer + 2 mid-turn
        self.assertEqual(rows["box questions replaced by a newer one before the owner answered"], 1)
        self.assertEqual(rows["messages of several lines (may be pasted output, not the owner's wording)"], 1)
        self.assertEqual(rows["of them sent while Claude was working"], 2)
        self.assertEqual(rows["short yes / no / done replies"], 3)
        self.assertEqual(rows["interruptions"], 1)
        self.assertEqual(rows["tool calls the owner refused"], 1)
        self.assertEqual(rows["shell commands the owner ran themself"], 2)

    def test_questions_stay_open_past_a_shell_command(self):
        shell = self.out.index("(ran a shell command themself)")
        block = self.out[shell:self.out.index("Yes, create it")]
        self.assertIn("Claude asked (box): Create the bucket?", block)

    def test_a_mid_turn_reply_takes_the_open_question(self):
        block = self.out[self.out.index("Is it switched on?"):]
        self.assertTrue(block.index("Owner: It's off") < block.index("password"))

    def test_replaced_questions_are_both_shown(self):
        block = self.out[self.out.index("First decision?"):self.out.index("When needed")]
        self.assertIn("Second decision?", block)

    def test_plain_words_after_password_stay_readable(self):
        self.assertIn("the password in the test tab, the passphrase is needed, password <redacted>", self.out)
        self.assertNotIn("hunter2x", self.out)

    def test_unanswered_at_the_end_is_listed(self):
        self.assertIn("## Still unanswered when the window ended", self.out)
        self.assertIn("(box) Left hanging?", self.out)

    def test_local_time_is_shown(self):
        self.assertIn(" UTC (", self.out)
        self.assertIn("local)", self.out)

    def test_long_messages_are_clipped(self):
        self.assertEqual(rd.clip("x" * 50, 10), "x" * 9 + "…")


if __name__ == "__main__":
    unittest.main(verbosity=1)
