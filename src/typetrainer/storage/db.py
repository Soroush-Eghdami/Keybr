# sqlite setup and tiny key-value store for things like unlocked letters
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

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
  delay_ms REAL,
  correct INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS key_stats(
  char TEXT PRIMARY KEY,
  ema_delay_ms REAL NOT NULL,
  timed_samples INTEGER NOT NULL,
  attempts INTEGER NOT NULL,
  errors INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS meta(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

DEFAULT_PATH = Path.home() / ".typetrainer" / "trainer.db"

# opens the db file and makes sure all tables exist, then migrates old files
def get_connection(path=None):
    p = Path(path) if path else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn

def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}

# migrates pre-5.5 databases: old key_stats(char, ema, samples, error_rate)
# becomes (char, ema, timed_samples, attempts, errors); delay_ms becomes nullable
def _migrate(conn):
    cols = _columns(conn, "key_stats")
    if cols and "timed_samples" not in cols:
        logger.info("migrating key_stats to schema v2")
        old = conn.execute("SELECT char, ema_delay_ms, samples, error_rate FROM key_stats").fetchall()
        conn.execute("DROP TABLE key_stats")
        conn.execute(
            "CREATE TABLE key_stats("
            " char TEXT PRIMARY KEY, ema_delay_ms REAL NOT NULL,"
            " timed_samples INTEGER NOT NULL, attempts INTEGER NOT NULL,"
            " errors INTEGER NOT NULL)"
        )
        for char, ema, samples, err_rate in old:
            try:
                samples = int(samples)
                errors = int(round(float(err_rate) * samples))
            except (TypeError, ValueError):
                logger.warning("dropping corrupt key_stats row for %r", char)
                continue
            conn.execute(
                "INSERT INTO key_stats(char, ema_delay_ms, timed_samples, attempts, errors)"
                " VALUES(?,?,?,?,?)",
                (char, float(ema), samples, samples, errors),
            )
        conn.commit()
    # keystrokes.delay_ms nullability: recreate only if still NOT NULL
    kcols = conn.execute("PRAGMA table_info(keystrokes)").fetchall()
    for cid, name, ctype, notnull, dflt, pk in kcols:
        if name == "delay_ms" and notnull:
            logger.info("migrating keystrokes.delay_ms to nullable")
            conn.execute("ALTER TABLE keystrokes RENAME TO keystrokes_old")
            conn.execute(
                "CREATE TABLE keystrokes("
                " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                " session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,"
                " expected TEXT NOT NULL, typed TEXT NOT NULL,"
                " delay_ms REAL, correct INTEGER NOT NULL)"
            )
            conn.execute(
                "INSERT INTO keystrokes(id, session_id, expected, typed, delay_ms, correct)"
                " SELECT id, session_id, expected, typed, delay_ms, correct FROM keystrokes_old"
            )
            conn.execute("DROP TABLE keystrokes_old")
            conn.commit()
            break
    set_meta(conn, "schema_version", str(SCHEMA_VERSION))

# reads one saved setting, empty string if it was never set
def get_meta(conn, key, default=""):
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    except sqlite3.OperationalError as exc:
        logger.warning("meta read failed for %r: %s", key, exc)
        return default
    return row[0] if row else default

# saves one setting, overwrites it if it already exists
def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
