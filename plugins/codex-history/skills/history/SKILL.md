---
name: history
description: Open a private local browser view of the current Codex conversation, with a searchable question index, jump navigation, readable Markdown and LaTeX, and an answers-only toggle. Use when the user invokes $history or asks to browse their conversation history.
---

# Codex History

Open the current conversation in the bundled local reader. This is a browser companion, not a native terminal popup. Codex CLI currently invokes this skill with `$history` or `/skills`; it does not support registering a plugin `/history` command.

1. Resolve `../../scripts/history.py` relative to this skill's directory to an absolute path.
2. Run `python3 "<absolute path to history.py>" open`. This defaults to a refreshable local reader and attempts to open the default browser in the same command. Its read-only server binds only to `127.0.0.1` and uses a random access token. Do not pass `--no-open` unless the user requests a link only. On Windows use `py -3` if `python3` is unavailable. The script uses `CODEX_THREAD_ID` and `CODEX_HOME` from the current session. It never guesses the newest session. For an explicitly selected conversation, pass `--thread-id` with its exact ID.
3. Read the result's `browserOpened` field. If true, briefly report that the open request was sent and return a clickable link using its `url`. If false, return the same link and explain that the reader is ready but browser launching was blocked or unavailable. Do not claim a browser opened based only on a running server. For offline mode, return a clickable local file link using the absolute `path` instead. Do not escalate permissions or silently replace a failed live reader with a snapshot.
4. Keep the response to one short sentence and the link; do not discuss or summarize the conversation. The page provides search, Enter-to-jump, an Answers only button, Alt+H, and copy buttons. Click **Refresh** to load newly saved messages directly while keeping the reading position; no new skill invocation is needed while the reader is running.

Do not read or summarize transcript contents into model context: the helper reads them directly and returns only a URL and process metadata. Do not export history into the project repository. If the current ID is unavailable, ask for the intended session ID or rollout file rather than opening another conversation. If Codex uses a custom `sqlite_home`, pass it with `--sqlite-home`. If local file or loopback access is blocked, report the actual error and use the host's normal permission workflow; never change sandbox settings or install dependencies automatically.

Python 3.9+ is the only launcher requirement; no pip/npm packages or API key are needed. The reader never modifies Codex data. Open tabs keep the server alive, including background tabs; it exits after two hours without an authenticated reader request. Browser launch or loopback access can still be blocked by the host sandbox. `open --live` remains an explicit alias for the default. For an explicitly requested offline reader, use `open --offline`; its snapshot is saved in a private temporary directory and cannot load newer messages. For SSH without existing port forwarding, use the offline mode and return the generated file path so the user can copy it to their local machine.

For an explicitly requested portable snapshot: `python3 "<script>" export --output "<user-chosen destination>.html"`. The HTML embeds the complete selected transcript and rendering assets. It opens offline in a browser without Python, a server, or additional installs; handle it as a private copy of the conversation. Existing output files are never overwritten.
