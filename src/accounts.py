"""
🧭 Wayfarer — accounts.py  (PHASE 2 — user database 👤)  ✅ demo-mode

THE WISHLIST: "have user database — sign-up/login, profiles, trip history".

LEARNING POINTS (read these twice):
    • SQLite = a database in ONE FILE (data/wayfarer.db) — perfect for projects.
    • Passwords are NEVER stored raw. We store salt + SHA-256(salt+password).
      Even if someone steals the database file, they can't read passwords.
    • secrets.token_hex() makes unpredictable salts/session tokens.

DEMO-MODE HONESTY: real products use battle-tested hashing (bcrypt/argon2)
and a real auth framework — this educational version shows the concepts.
"""

import hashlib
import secrets
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "wayfarer.db"      # gitignored — data stays local

# Windows consoles default to cp1252, which can't print emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_schema = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    salt        TEXT NOT NULL,
    password    TEXT NOT NULL,
    created     TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS trips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    origin      TEXT, destination TEXT,
    days        INTEGER, total_km REAL, style TEXT,
    created     TEXT DEFAULT (datetime('now'))
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the DB and make sure the tables exist."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.executescript(_schema)
    return conn


def _hash(password: str, salt: str) -> str:
    """Salted SHA-256 — same password + different salt = different hash."""
    return hashlib.sha256((salt + password).encode()).hexdigest()


# ---------------------------------------------------------------- #
#  Public API                                                        #
# ---------------------------------------------------------------- #
def signup(username: str, password: str, db_path: Path | None = None) -> dict:
    """Create an account. Returns {'ok': True, 'user_id': id} or an error."""
    if len(username.strip()) < 3:
        return {"ok": False, "error": "Username needs at least 3 characters."}
    if len(password) < 4:
        return {"ok": False, "error": "Password needs at least 4 characters."}
    salt = secrets.token_hex(8)
    with _connect(db_path) as conn:
        try:
            conn.execute("INSERT INTO users (username, salt, password) VALUES (?,?,?)",
                         (username.strip(), salt, _hash(password, salt)))
        except sqlite3.IntegrityError:
            return {"ok": False, "error": f"Username '{username}' is already taken."}
        uid = conn.execute("SELECT id FROM users WHERE username=?",
                           (username.strip(),)).fetchone()[0]
    return {"ok": True, "user_id": uid, "username": username.strip()}


def login(username: str, password: str, db_path: Path | None = None) -> dict:
    """Check credentials. Wrong password NEVER tells which half was wrong."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT id, salt, password FROM users WHERE username=?",
                           (username.strip(),)).fetchone()
    if not row or _hash(password, row[1]) != row[2]:
        return {"ok": False, "error": "Wrong username or password."}
    return {"ok": True, "user_id": row[0], "username": username.strip(),
            "session": secrets.token_hex(8)}


def save_trip(user_id: int, origin: str, destination: str, days: int,
              total_km: float, style: str, db_path: Path | None = None) -> None:
    """Remember a planned trip on the user's profile (trip history)."""
    with _connect(db_path) as conn:
        conn.execute("INSERT INTO trips (user_id, origin, destination, days, total_km, style)"
                     " VALUES (?,?,?,?,?,?)",
                     (user_id, origin, destination, int(days), float(total_km), style))


def trip_history(user_id: int, db_path: Path | None = None) -> pd.DataFrame:
    """All trips a user has planned, newest first."""
    with _connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT origin, destination, days, total_km, style, created "
            "FROM trips WHERE user_id=? ORDER BY created DESC", conn, params=(user_id,))


# ---------------------------------------------------------------- #
#  Test drive                                                        #
# ---------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "test.db"   # throwaway DB for the demo

    print("=== signup / login round-trip ===")
    print(signup("aditi", "trip123", tmp))
    print(signup("aditi", "again123", tmp))       # duplicate → refused
    print(login("aditi", "trip123", tmp))         # correct
    print(login("aditi", "WRONG", tmp))           # wrong → refused, no hints
    assert signup("aditi", "trip123", tmp)["ok"] is False
    assert login("aditi", "trip123", tmp)["ok"] is True
    assert login("aditi", "WRONG", tmp)["ok"] is False

    print("\n=== trip history ===")
    uid = login("aditi", "trip123", tmp)["user_id"]
    save_trip(uid, "Berhampur", "Berhampur", 5, 2698, "comfort", tmp)
    save_trip(uid, "Tokyo", "Tokyo", 12, 2224, "premium", tmp)
    print(trip_history(uid, tmp).to_string(index=False))
    assert len(trip_history(uid, tmp)) == 2

    print("\n🎉 ALL ACCOUNT TESTS PASSED (demo-mode auth works)")
