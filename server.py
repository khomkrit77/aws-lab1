#!/usr/bin/env python3
"""Maze Munch: static game server with a tiny SQLite progress API."""
import json
import os
import re
import sqlite3
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "data", "maze-munch.sqlite3"))
PORT = int(os.environ.get("PORT", "8000"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def connect():
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_database():
    with connect() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY COLLATE NOCASE,
                difficulty TEXT NOT NULL DEFAULT 'normal',
                unlocked_level INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS level_scores (
                account_name TEXT NOT NULL COLLATE NOCASE,
                level INTEGER NOT NULL CHECK (level > 0),
                best_score INTEGER NOT NULL DEFAULT 0,
                cleared INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (account_name, level),
                FOREIGN KEY (account_name) REFERENCES accounts(name) ON DELETE CASCADE
            )
        """)


def profile_for(db, name):
    account = db.execute(
        "SELECT name, difficulty, unlocked_level FROM accounts WHERE name = ?",
        (name,),
    ).fetchone()
    if not account:
        return None
    scores = db.execute(
        "SELECT level, best_score, cleared, attempts FROM level_scores "
        "WHERE account_name = ? ORDER BY level",
        (account["name"],),
    ).fetchall()
    return {
        "name": account["name"],
        "difficulty": account["difficulty"],
        "unlockedLevel": account["unlocked_level"],
        "scores": [
            {
                "level": row["level"],
                "bestScore": row["best_score"],
                "cleared": bool(row["cleared"]),
                "attempts": row["attempts"],
            }
            for row in scores
        ],
    }


class GameHandler(SimpleHTTPRequestHandler):
    server_version = "MazeMunch/1.0"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length")
        if length < 1 or length > 8192:
            raise ValueError("Request body must be between 1 and 8192 bytes")
        try:
            data = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Request body must be valid JSON")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json(200, {"ok": True})
        if parsed.path == "/api/profile":
            name = parse_qs(parsed.query).get("name", [""])[0].strip()
            if not name:
                return self.send_json(400, {"error": "Enter a player name"})
            with connect() as db:
                profile = profile_for(db, name)
            if not profile:
                return self.send_json(404, {"error": "Player not found"})
            return self.send_json(200, profile)
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            if parsed.path == "/api/profile":
                return self.save_profile(data)
            if parsed.path == "/api/score":
                return self.save_score(data)
            return self.send_json(404, {"error": "Unknown API endpoint"})
        except ValueError as error:
            return self.send_json(400, {"error": str(error)})
        except sqlite3.Error:
            return self.send_json(500, {"error": "Database request failed"})

    def save_profile(self, data):
        name = str(data.get("name", "")).strip()
        difficulty = str(data.get("difficulty", "normal")).strip().lower()
        if not re.fullmatch(r"[\wก-๙][\wก-๙ .-]{0,23}", name, flags=re.UNICODE):
            return self.send_json(400, {"error": "Name must be 1–24 characters"})
        if difficulty not in ("easy", "normal", "hard"):
            return self.send_json(400, {"error": "Choose easy, normal, or hard"})
        with connect() as db:
            db.execute(
                "INSERT INTO accounts(name, difficulty) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET difficulty=excluded.difficulty, "
                "updated_at=CURRENT_TIMESTAMP",
                (name, difficulty),
            )
            profile = profile_for(db, name)
        return self.send_json(200, profile)

    def save_score(self, data):
        name = str(data.get("name", "")).strip()
        try:
            level = int(data.get("level", 0))
            score = int(data.get("score", -1))
        except (TypeError, ValueError):
            return self.send_json(400, {"error": "Level and score must be numbers"})
        cleared = bool(data.get("cleared", False))
        if level < 1 or level > 100 or score < 0 or score > 100000000:
            return self.send_json(400, {"error": "Level or score is out of range"})
        with connect() as db:
            account = db.execute(
                "SELECT unlocked_level FROM accounts WHERE name = ?", (name,)
            ).fetchone()
            if not account:
                return self.send_json(404, {"error": "Player not found"})
            if level > account["unlocked_level"]:
                return self.send_json(409, {"error": "This level is still locked"})
            db.execute(
                "INSERT INTO level_scores(account_name, level, best_score, cleared, attempts) "
                "VALUES (?, ?, ?, ?, 1) "
                "ON CONFLICT(account_name, level) DO UPDATE SET "
                "best_score=MAX(level_scores.best_score, excluded.best_score), "
                "cleared=MAX(level_scores.cleared, excluded.cleared), "
                "attempts=level_scores.attempts + 1, updated_at=CURRENT_TIMESTAMP",
                (name, level, score, int(cleared)),
            )
            if cleared:
                db.execute(
                    "UPDATE accounts SET unlocked_level=MAX(unlocked_level, ?), "
                    "updated_at=CURRENT_TIMESTAMP WHERE name = ?",
                    (level + 1, name),
                )
            profile = profile_for(db, name)
        return self.send_json(200, profile)

    def log_message(self, format_string, *args):
        print("%s - %s" % (self.address_string(), format_string % args))


initialize_database()
handler = partial(GameHandler, directory=BASE_DIR)
print("Maze Munch listening on 0.0.0.0:%s" % PORT, flush=True)
ThreadingHTTPServer(("0.0.0.0", PORT), handler).serve_forever()
