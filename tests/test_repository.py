# sqlite round trip + legacy migration, using :memory:
import sqlite3
from typetrainer.engine.session import Session
from typetrainer.engine.stats import StatsTracker
from typetrainer.storage import db
from typetrainer.storage.repository import load_key_stats, save_session, upsert_key_stats

def _mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(db.SCHEMA)
    db._migrate(conn)
    return conn

def test_round_trip_with_none_delay():
    conn = _mem_conn()
    s = Session("hi")
    s.type_char("h", now=0.0)
    s.type_char("i", now=0.2)
    res = s.result(now=0.2)
    sid = save_session(conn, res, s.keystrokes)
    assert sid == 1
    rows = conn.execute("SELECT expected, typed, delay_ms, correct FROM keystrokes").fetchall()
    assert rows[0][2] is None
    assert rows[1][2] is not None

def test_key_stats_round_trip_counts():
    conn = _mem_conn()
    t = StatsTracker()
    t.record("a", 200.0, True)
    t.record("a", 150.0, False)
    upsert_key_stats(conn, list(t.stats.values()))
    rows = load_key_stats(conn)
    assert rows[0] == ("a", t.stats["a"].ema_delay_ms, 1, 2, 1)
    t2 = StatsTracker()
    t2.load_rows(rows)
    assert t2.stats["a"].timed_samples == 1
    assert t2.stats["a"].attempts == 2
    assert t2.stats["a"].errors == 1

def test_legacy_migration():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TABLE key_stats(char TEXT PRIMARY KEY, ema_delay_ms REAL NOT NULL, samples INTEGER NOT NULL, error_rate REAL NOT NULL)")
    conn.execute("CREATE TABLE keystrokes(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, expected TEXT NOT NULL, typed TEXT NOT NULL, delay_ms REAL NOT NULL, correct INTEGER NOT NULL)")
    conn.execute("CREATE TABLE sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL DEFAULT (datetime('now')), wpm REAL NOT NULL, accuracy REAL NOT NULL, duration_s REAL NOT NULL, chars INTEGER NOT NULL)")
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO key_stats VALUES('a', 250.0, 10, 0.2)")
    conn.commit()
    conn.executescript("CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL DEFAULT (datetime('now')), wpm REAL NOT NULL, accuracy REAL NOT NULL, duration_s REAL NOT NULL, chars INTEGER NOT NULL);")
    db._migrate(conn)
    rows = conn.execute("SELECT char, ema_delay_ms, timed_samples, attempts, errors FROM key_stats").fetchall()
    assert rows[0] == ("a", 250.0, 10, 10, 2)
    assert db.get_meta(conn, "schema_version") == str(db.SCHEMA_VERSION)
