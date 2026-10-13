#!/usr/bin/env python3
"""Serve the static preview with live reload, rebuilding and validating on save."""

import argparse
import json
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root = Path(__file__).resolve().parents[1]
web = root / "web"
# Files written by web/build.py; watching them would trigger endless rebuilds.
generated = {web / "data/sources.json", web / "data/guides.json", web / "data/topics.json",
             web / "assets/CONTRIBUTING.md", web / "assets/mr-safety-agent.zip"}
# Changes here require copying fresh content into web/ before reloading.
build_inputs = [root / "skills", root / "content", root / "CONTRIBUTING.md", root / "LICENSE"]
watched = build_inputs + [web, root / "evals", root / "scripts/validate.py", *root.glob("*.md")]
ignored_parts = {"__pycache__", ".DS_Store", "local-runs"}

CLIENT = """<script>(() => {
  const show = s => {
    let bar = document.getElementById('__dev_status');
    if (s.ok) { bar && bar.remove(); return; }
    bar = bar || Object.assign(document.createElement('pre'), {id: '__dev_status'});
    bar.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:99999;margin:0;padding:12px 16px;'
      + 'max-height:40vh;overflow:auto;background:#7f1d1d;color:#fff;font:13px/1.4 ui-monospace,monospace;white-space:pre-wrap';
    bar.textContent = s.message;
    document.body.append(bar);
  };
  let version = null;
  const events = new EventSource('/__livereload');
  events.onmessage = e => {
    const s = JSON.parse(e.data);
    if (version !== null && s.version !== version) return location.reload();
    version = s.version; show(s);
  };
})();</script>"""


class State:
    def __init__(self):
        self.changed = threading.Condition()
        self.status = {"version": 0, "ok": True, "message": ""}

    def publish(self, ok, message):
        with self.changed:
            self.status = {"version": self.status["version"] + 1, "ok": ok, "message": message}
            self.changed.notify_all()


def run(script):
    result = subprocess.run([sys.executable, str(root / script)], cwd=root,
                            capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def refresh(state, rebuild):
    messages, ok = [], True
    if rebuild:
        built, output = run("web/build.py")
        ok &= built
        messages.append(output)
    valid, output = run("scripts/validate.py")
    ok &= valid
    messages.append(output)
    message = "\n".join(messages)
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
    state.publish(ok, message)


def snapshot():
    files = {}
    for base in watched:
        for path in [base] if base.is_file() else base.rglob("*") if base.is_dir() else []:
            if (path.is_file() and path not in generated and not path.is_relative_to(web / "guides") and not path.is_relative_to(web / "topics")
                    and not ignored_parts & set(path.parts)):
                try:
                    files[path] = path.stat().st_mtime_ns
                except OSError:
                    pass
    return files


def watch(state, interval):
    previous = snapshot()
    while True:
        time.sleep(interval)
        current = snapshot()
        changes = {p for p in previous.keys() | current.keys() if previous.get(p) != current.get(p)}
        previous = current
        if changes:
            names = ", ".join(sorted(str(p.relative_to(root)) for p in changes)[:5])
            print(f"[{time.strftime('%H:%M:%S')}] Changed: {names}", flush=True)
            refresh(state, any(p.is_relative_to(b) for p in changes for b in build_inputs))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, state, **kwargs):
        self.state = state
        super().__init__(*args, directory=str(web), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/__livereload":
            return self.stream_events()
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / "index.html"
        if path.suffix == ".html" and path.is_file():
            html = path.read_text(encoding="utf-8")
            marker = "</body>" if "</body>" in html else None
            html = html.replace(marker, CLIENT + marker, 1) if marker else html + CLIENT
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        sent = None
        try:
            while True:
                with self.state.changed:
                    if sent == self.state.status["version"]:
                        self.state.changed.wait(timeout=15)
                    status = dict(self.state.status)
                if status["version"] == sent:
                    self.wfile.write(b": keep-alive\n\n")
                else:
                    self.wfile.write(f"data: {json.dumps(status)}\n\n".encode("utf-8"))
                    sent = status["version"]
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between file checks")
    args = parser.parse_args()
    state = State()
    refresh(state, rebuild=True)
    threading.Thread(target=watch, args=(state, args.interval), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, state=state))
    server.daemon_threads = True
    print(f"Live preview at http://127.0.0.1:{args.port}/ (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    sys.exit(main())
