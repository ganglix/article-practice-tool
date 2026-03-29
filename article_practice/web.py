from __future__ import annotations

import argparse
import errno
from functools import partial
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser

from .core import Exercise, build_exercise, grade_exercise


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
SESSION_STORE: dict[str, Exercise] = {}


class ArticlePracticeHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, directory: Path | None = None, **kwargs):
        self.directory = directory or STATIC_DIR
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._serve_file("index.html", "text/html; charset=utf-8")
            return

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return

        if path == "/app.css":
            self._serve_file("app.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/exercises":
            self._handle_create_exercise()
            return

        if path == "/api/grade":
            self._handle_grade()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _handle_create_exercise(self) -> None:
        payload = self._read_json()
        if payload is None:
            return

        try:
            exercise = build_exercise(str(payload.get("text", "")))
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        _prune_sessions()
        SESSION_STORE[exercise.exercise_id] = exercise
        self._send_json(HTTPStatus.CREATED, exercise.prompt_payload())

    def _handle_grade(self) -> None:
        payload = self._read_json()
        if payload is None:
            return

        exercise_id = str(payload.get("exercise_id", ""))
        exercise = SESSION_STORE.get(exercise_id)
        if exercise is None:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {"error": "Exercise not found. Generate a new one and try again."},
            )
            return

        answers = payload.get("answers", [])
        if not isinstance(answers, list) or not all(isinstance(item, str) for item in answers):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Answers must be submitted as a list of strings."},
            )
            return

        try:
            result = grade_exercise(exercise, answers)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, result)

    def _read_json(self) -> dict | None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload."})
            return None

    def _serve_file(self, filename: str, content_type: str) -> None:
        file_path = self.directory / filename
        if not file_path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _prune_sessions(max_sessions: int = 200) -> None:
    if len(SESSION_STORE) < max_sessions:
        return

    oldest_ids = sorted(SESSION_STORE, key=lambda item: SESSION_STORE[item].created_at)[:20]
    for exercise_id in oldest_ids:
        SESSION_STORE.pop(exercise_id, None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Article Practice local web app.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port to serve on. Use 0 to let the OS choose an available port.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the app in your default browser after starting the server.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = partial(ArticlePracticeHandler, directory=STATIC_DIR)
    try:
        server = ThreadingHTTPServer((args.host, args.port), handler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(
                f"Port {args.port} is already in use on {args.host}. "
                f"Stop the existing server or run "
                f"`python3 -m article_practice --port 0 --open-browser`."
            )
            return 1
        raise

    bound_host, bound_port = server.server_address[:2]
    url = f"http://{bound_host}:{bound_port}"

    print(f"Article Practice is available at {url}")
    if args.open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
    return 0
