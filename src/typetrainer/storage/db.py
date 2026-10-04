# sqlite setup and tiny key-value store for things like unlocked letters
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  wpm REAL NOT NULL,
  accuracy REAL NOT NULL,
  duration_s REAL NOT NULL,
  chars INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS keystrokes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  expected TEXT NOT NULL,
  typed TEXT NOT NULL,
  delay_ms REAL NOT NULL,
  correct INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS key_stats(
  char TEXT PRIMARY KEY,
  ema_delay_ms REAL NOT NULL,
  samples INTEGER NOT NULL,
  error_rate REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

DEFAULT_PATH = Path.home() / ".typetrainer" / "trainer.db"

# opens the db file and makes sure all tables exist
def get_connection(path=None):
    p = Path(path) if path else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn

# reads one saved setting, empty string if it was never set
def get_meta(conn, key, default=""):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default

# saves one setting, overwrites it if it already exists
def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
