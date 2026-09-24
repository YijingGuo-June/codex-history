#!/usr/bin/env python3
"""Launch the local, read-only Codex History viewer. Python 3.9+, no dependencies."""

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit, parse_qs
import webbrowser

from history_reader import HistoryError, HistoryStore, entry, package
from standalone import build_html

ASSETS = Path(__file__).resolve().parent.parent / "assets"


class DemoStore:
    def read(self):
        return package("demo-conversation", [
            entry("user", "How does the cache work?\nExplain the request lifecycle, including expiration."),
            entry("assistant", "I'll trace the cache lookup and expiry path.", "commentary"),
            entry("tool", "$ rg -n 'cache' src/\nsrc/cache.py:24: class Cache"),
            entry("reasoning", "Inspecting the cache lookup and expiration checks."),
            entry("assistant", "## Request lifecycle\n\n1. Look up the request key.\n2. Return the cached value if it has not expired.\n3. Otherwise fetch, store, and return a fresh value.\n\n```python\nif entry and entry.expires_at > now:\n    return entry.value\n```\n\nExpiration is checked on each read.", "final_answer"),
            entry("user", "如果缓存过期，多个请求同时进来会发生什么？"),
            entry("tool", "$ python -m unittest tests.test_cache\nRan 6 tests\nOK"),
            entry("assistant", "多个请求可能同时重新计算同一个结果。可以用锁合并这些请求，让后续请求等待第一次计算完成。\n\n**注意：** 锁应按缓存键划分，避免不同请求互相阻塞。\n\n## 平均请求耗时\n\n设缓存命中率为 $p$，则平均延迟可以表示为：\n\n$$\\mathbb{E}[T] = p \\cdot T_{\\mathrm{hit}} + (1-p) \\cdot T_{\\mathrm{miss}}$$\n\n| Scenario | Expected behavior |\n| :--- | :--- |\n| Fresh cache | Return immediately |\n| Concurrent misses | Share one refresh |\n| Refresh failure | Release the lock |", "final_answer"),
            entry("user", "Show me the edge cases and the test plan."),
            entry("assistant", "## Test plan\n\n- Fresh entry: return the cached value.\n- Expired entry: refresh once.\n- Concurrent requests: share the same refresh.\n- Failed refresh: release the lock and report the error.\n\n```python\nassert cache.get('missing') is None\n```", "final_answer"),
            entry("user", "What should we change next?"),
            entry("assistant", "Add a concurrency test before changing the lock implementation. Keep the cache interface stable so existing callers continue to work.", "final_answer"),
        ], "Demo")


def make_handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            # URLs contain a bearer token; don't put them in access logs.
            pass

        def send(self, status, body, kind="text/plain; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; img-src data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            expected_host = "127.0.0.1:{}".format(self.server.server_port)
            if self.headers.get("Host") != expected_host:
                return self.send(403, b"Invalid host")
            if self.headers.get("Origin") not in (None, "http://" + expected_host):
                return self.send(403, b"Invalid origin")
            request = urlsplit(self.path)
            if request.path.startswith("/vendor/"):
                # Public, bundled rendering libraries only; no conversation data.
                asset = (ASSETS / request.path.lstrip("/")).resolve()
                vendor = (ASSETS / "vendor").resolve()
                mime = {".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf"}.get(asset.suffix)
                if asset.is_relative_to(vendor) and asset.is_file() and mime:
                    return self.send(200, asset.read_bytes(), mime)
                return self.send(404, b"Not found")
            supplied = parse_qs(request.query).get("token", [""])[0]
            if not hmac.compare_digest(supplied.encode(), token.encode()):
                return self.send(403, b"Open the private viewer link printed by Codex History.")
            if request.path == "/api/history":
                try:
                    body = json.dumps(store.read(), ensure_ascii=False).encode()
                    self.send(200, body, "application/json; charset=utf-8")
                except (HistoryError, OSError, ValueError) as exc:
                    self.send(503, json.dumps({"error": str(exc)}).encode(), "application/json")
            elif request.path in ("/", "/viewer.js", "/viewer.css"):
                filename, mime = {"/": ("viewer.html", "text/html; charset=utf-8"),
                                  "/viewer.js": ("viewer.js", "text/javascript; charset=utf-8"),
                                  "/viewer.css": ("viewer.css", "text/css; charset=utf-8")}[request.path]
                body = (ASSETS / filename).read_bytes()
                if request.path == "/":
                    body = body.replace(b"__TOKEN__", token.encode())
                self.send(200, body, mime)
            else:
                self.send(404, b"Not found")
    return Handler


def serve(args, ready=None):
    store = DemoStore() if args.demo else HistoryStore(args.thread_id, args.home, args.sqlite_home, args.file)
    store.read()  # Fail before reporting a usable link.
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, token))
    server.daemon_threads = True
    url = "http://127.0.0.1:{}/?token={}".format(server.server_port, token)
    if ready:
        # Release the startup log before the launcher removes its temp directory
        # (Windows cannot unlink a file still held open by the child).
        with open(os.devnull, "w") as null:
            os.dup2(null.fileno(), sys.stderr.fileno())
        ready.write_text(json.dumps({"url": url, "pid": os.getpid()}), encoding="utf-8")
    else:
        print(url, flush=True)
    if not args.no_open and not ready:
        webbrowser.open(url)
    timer = threading.Timer(args.lifetime, server.shutdown)
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        timer.cancel()
        server.server_close()


def launch(args):
    with tempfile.TemporaryDirectory(prefix="codex-history-") as directory:
        ready = Path(directory) / "ready.json"
        command = [sys.executable, str(Path(__file__).resolve()), "serve", "--no-open",
                   "--ready-file", str(ready), "--lifetime", str(args.lifetime)]
        for name in ("thread_id", "home", "sqlite_home", "file"):
            value = getattr(args, name)
            if value:
                command.extend(["--" + name.replace("_", "-"), value])
        if args.demo:
            command.append("--demo")
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        with (Path(directory) / "startup.log").open("w+") as log:
            child = subprocess.Popen(command, stderr=log, **kwargs)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if ready.exists():
                    try:
                        result = json.loads(ready.read_text(encoding="utf-8"))
                        break
                    except json.JSONDecodeError:
                        pass
                if child.poll() is not None:
                    log.seek(0)
                    raise HistoryError(log.read().strip() or "Viewer failed to start.")
                time.sleep(0.05)
            else:
                child.terminate()
                child.wait(timeout=5)
                raise HistoryError("Viewer startup timed out.")
        result["expiresInSeconds"] = args.lifetime
        result["browserOpened"] = False if args.no_open else webbrowser.open(result["url"])
        print(json.dumps(result, ensure_ascii=False))


def open_snapshot(args):
    """Open a portable snapshot without binding sockets or starting a daemon."""
    store = DemoStore() if args.demo else HistoryStore(args.thread_id, args.home, args.sqlite_home, args.file)
    data = store.read()
    directory = Path(tempfile.mkdtemp(prefix="codex-history-view-"))
    destination = directory / "history.html"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(build_html(data))
    destination.chmod(0o600)
    result = {"mode": "offline", "path": str(destination), "url": destination.as_uri(), "browserOpened": False}
    if not args.no_open:
        try:
            result["browserOpened"] = webbrowser.open(result["url"])
        except (OSError, webbrowser.Error) as exc:
            result["browserOpenError"] = str(exc)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("open", "serve", "check", "export"), nargs="?", default="open")
    parser.add_argument("--thread-id", help="Exact conversation ID (default: CODEX_THREAD_ID)")
    parser.add_argument("--home", help="Codex data directory (default: CODEX_HOME or ~/.codex)")
    parser.add_argument("--sqlite-home", help="Directory containing Codex SQLite databases, if customized")
    parser.add_argument("--file", help="Read one legacy rollout JSONL file instead of SQLite")
    parser.add_argument("--demo", action="store_true", help="Use synthetic data; never access your sessions")
    parser.add_argument("--no-open", action="store_true", help="Print a private URL without opening a browser")
    parser.add_argument("--live", action="store_true", help="Use the optional loopback server instead of the default offline snapshot")
    parser.add_argument("--output", help="HTML destination for export; existing files are never overwritten")
    parser.add_argument("--lifetime", type=int, default=7200, help="Server lifetime in seconds (default: 7200)")
    parser.add_argument("--ready-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.lifetime < 1:
        parser.error("--lifetime must be positive")
    try:
        if args.command == "export":
            if not args.output:
                parser.error("export requires --output destination.html")
            data = DemoStore().read() if args.demo else HistoryStore(args.thread_id, args.home, args.sqlite_home, args.file).read()
            destination = Path(args.output).expanduser().resolve()
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(build_html(data))
            print(str(destination))
        elif args.command == "check":
            data = DemoStore().read() if args.demo else HistoryStore(args.thread_id, args.home, args.sqlite_home, args.file).read()
            print(json.dumps({"source": data["source"], "questions": len(data["questions"]),
                              "messages": len(data["messages"]), "warnings": data["warnings"]}))
        elif args.command == "serve":
            serve(args, Path(args.ready_file) if args.ready_file else None)
        elif args.live:
            launch(args)
        else:
            open_snapshot(args)
    except (HistoryError, OSError, ValueError) as exc:
        print("Codex History: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
