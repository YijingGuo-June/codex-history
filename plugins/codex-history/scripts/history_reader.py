"""Read one explicitly selected Codex conversation without modifying its storage."""

import hashlib
import json
import os
from pathlib import Path
import sqlite3


class HistoryError(Exception):
    pass


def text_content(content):
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict):
            if isinstance(part.get("text"), str):
                parts.append(part["text"])
            elif part.get("type") in ("image", "input_image", "localImage", "local_image"):
                parts.append("[Image attachment]")
            elif part.get("type") in ("skill", "mention"):
                parts.append("[{}: {}]".format(part["type"], part.get("name", "")))
    return "\n".join(parts)


def entry(kind, text, phase=None, timestamp=None):
    if kind == "user" and text.strip().startswith("<send_user_message_question_reply>") and text.strip().endswith("</send_user_message_question_reply>"):
        # Desktop clarification replies are persisted as a transport envelope.
        # Show the human answer and its question, not internal UI identifiers.
        raw = text.strip()[len("<send_user_message_question_reply>"):-len("</send_user_message_question_reply>")]
        try:
            replies = json.loads(raw)
            if isinstance(replies, list) and replies and all(isinstance(r, dict) and isinstance(r.get("answer"), str) and isinstance(r.get("question"), str) for r in replies):
                text = "\n\n".join(r["answer"] + "\n\n> " + r["question"].replace("\n", "\n> ") for r in replies)
        except json.JSONDecodeError:
            pass
    return {"kind": kind, "text": text, "phase": phase, "timestamp": timestamp}


def normalize_item(item, timestamp=None):
    """Decode public thread items. Never expose encrypted/raw reasoning payloads."""
    kind = item.get("type")
    if kind == "userMessage":
        return entry("user", text_content(item.get("content")), timestamp=timestamp)
    if kind == "agentMessage":
        return entry("assistant", item.get("text", ""), item.get("phase") or "final_answer", timestamp)
    if kind == "reasoning":
        return entry("reasoning", text_content(item.get("summary")), timestamp=timestamp)
    if kind == "commandExecution":
        text = "$ " + item.get("command", "")
        if item.get("aggregatedOutput"):
            text += "\n" + item["aggregatedOutput"]
        return entry("tool", text, timestamp=timestamp)
    if kind in ("mcpToolCall", "dynamicToolCall"):
        label = "{} / {}".format(item.get("server", "tool"), item.get("tool", ""))
        fields = {k: item[k] for k in ("arguments", "result", "error") if item.get(k) is not None}
        return entry("tool", label + "\n" + json.dumps(fields, ensure_ascii=False, indent=2), timestamp=timestamp)
    if kind in ("fileChange", "webSearch", "imageView", "imageGeneration", "collabAgentToolCall", "plan"):
        fields = {k: v for k, v in item.items() if k not in ("id", "type")}
        return entry("tool", kind + "\n" + json.dumps(fields, ensure_ascii=False, indent=2), timestamp=timestamp)
    if kind in ("contextCompaction", "enteredReviewMode", "exitedReviewMode"):
        return entry("status", kind, timestamp=timestamp)
    return None


def read_sqlite(path, thread_id):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
        conn.execute("PRAGMA query_only = ON")
        rows = conn.execute(
            "SELECT item_json, created_at_ms FROM thread_items "
            "WHERE thread_id = ? ORDER BY rollout_ordinal", (thread_id,)
        ).fetchall()
    messages = []
    for raw, timestamp in rows:
        item = normalize_item(json.loads(raw), timestamp)
        if item is not None:
            messages.append(item)
    return messages


def read_rollout(path):
    records = []
    warnings = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
            except json.JSONDecodeError:
                # A concurrent writer may not have finished the last line yet.
                warnings.append("Skipped incomplete/invalid JSONL line {}.".format(number))
    event_users = any(r.get("type") == "event_msg" and r.get("payload", {}).get("type") == "user_message" for r in records)
    response_agents = any(r.get("type") == "response_item" and r.get("payload", {}).get("role") == "assistant" for r in records)
    messages = []
    calls = {}
    for record in records:
        payload = record.get("payload", {})
        kind = payload.get("type")
        timestamp = record.get("timestamp")
        message = None
        if record.get("type") == "event_msg":
            if kind == "user_message":
                text = payload.get("message", "")
                if payload.get("images") or payload.get("local_images"):
                    text += "\n[Image attachment]"
                message = entry("user", text, timestamp=timestamp)
            elif kind == "agent_message" and not response_agents:
                message = entry("assistant", payload.get("message", ""), payload.get("phase") or "final_answer", timestamp)
        elif record.get("type") == "response_item":
            if kind == "message":
                role = payload.get("role")
                text = text_content(payload.get("content"))
                if role == "user" and not event_users:
                    if not text.lstrip().startswith(("# AGENTS.md instructions", "<environment_context>", "<permissions instructions>", "<user_instructions>")):
                        message = entry("user", text, timestamp=timestamp)
                elif role == "assistant":
                    message = entry("assistant", text, payload.get("phase") or "final_answer", timestamp)
            elif kind == "reasoning":
                message = entry("reasoning", text_content(payload.get("summary")), timestamp=timestamp)
            elif kind in ("function_call", "custom_tool_call", "web_search_call"):
                arguments = payload.get("arguments", payload.get("input", payload.get("action", "")))
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False, indent=2)
                message = entry("tool", payload.get("name", kind) + "\n" + arguments, timestamp=timestamp)
                calls[payload.get("call_id", payload.get("id"))] = message
            elif kind in ("function_call_output", "custom_tool_call_output"):
                output = payload.get("output", "")
                if not isinstance(output, str):
                    output = json.dumps(output, ensure_ascii=False, indent=2)
                call = calls.get(payload.get("call_id"))
                if call is not None:
                    call["text"] += "\n\n" + output
                else:
                    message = entry("tool", output, timestamp=timestamp)
        if message is not None:
            messages.append(message)
    return messages, warnings


def package(thread_id, messages, source, warnings=None):
    questions = []
    for i, message in enumerate(messages):
        message["id"] = "message-{}".format(i)
        if message["kind"] == "user":
            number = len(questions) + 1
            message["question"] = number
            questions.append({"number": number, "messageId": message["id"], "text": message["text"]})
    content = {"threadId": thread_id, "messages": messages, "questions": questions,
               "source": source, "warnings": warnings or []}
    content["revision"] = hashlib.sha256(json.dumps(content, ensure_ascii=False).encode()).hexdigest()[:20]
    return content


class HistoryStore:
    def __init__(self, thread_id=None, home=None, sqlite_home=None, rollout=None):
        self.home = Path(home or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
        self.sqlite_home = Path(sqlite_home).expanduser() if sqlite_home else self.home
        self.thread_id = thread_id or (os.environ.get("CODEX_THREAD_ID") if not rollout else None)
        self.rollout = Path(rollout).expanduser().resolve() if rollout else None
        if not self.thread_id and not self.rollout:
            raise HistoryError("No current conversation ID. Pass --thread-id UUID or --file rollout.jsonl; the latest session is never guessed.")

    def find_rollout(self):
        if self.rollout:
            return self.rollout
        # The metadata database knows archived and custom rollout paths.
        for database in sorted(self.sqlite_home.glob("state_*.sqlite"), reverse=True):
            try:
                with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
                    row = conn.execute("SELECT rollout_path FROM threads WHERE id = ?", (self.thread_id,)).fetchone()
                if row and row[0] and Path(row[0]).is_file():
                    return Path(row[0])
            except sqlite3.Error:
                continue
        # Compare literal filenames rather than interpolating an ID into a glob.
        for directory in ("sessions", "archived_sessions"):
            for path in (self.home / directory).rglob("*.jsonl"):
                if path.name.endswith("-" + self.thread_id + ".jsonl"):
                    return path
        return None

    def read(self):
        warnings = []
        if not self.rollout:
            database = self.sqlite_home / "thread_history_1.sqlite"
            if database.is_file():
                try:
                    messages = read_sqlite(database, self.thread_id)
                    if messages:
                        return package(self.thread_id, messages, "SQLite")
                except (sqlite3.Error, ValueError) as exc:
                    warnings.append("SQLite history unavailable ({}); trying JSONL.".format(type(exc).__name__))
        path = self.find_rollout()
        if path is None or not path.is_file():
            raise HistoryError("No readable history found for this conversation. Check --home/--sqlite-home, or pass --file explicitly.")
        messages, notes = read_rollout(path)
        return package(self.thread_id or path.stem, messages, "JSONL", warnings + notes)
