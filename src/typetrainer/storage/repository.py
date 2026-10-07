# saving and loading rounds and key stats from sqlite
from ..engine.session import Keystroke, SessionResult
from ..engine.stats import KeyStat

# stores one finished round plus every keypress in it, returns the new round id
def save_session(conn, result, keystrokes):
    cur = conn.execute(
        "INSERT INTO sessions(wpm, accuracy, duration_s, chars) VALUES(?,?,?,?)",
        (result.wpm, result.accuracy, result.elapsed_seconds, result.correct_chars),
    )
    sid = cur.lastrowid
    conn.executemany(
        "INSERT INTO keystrokes(session_id, expected, typed, delay_ms, correct) VALUES(?,?,?,?,?)",
        [(sid, k.expected, k.typed, k.delay_ms, int(k.correct)) for k in keystrokes],
    )
    conn.commit()
    return int(sid)

# writes the whole stats table, updating keys you already had (counts, not rates)
def upsert_key_stats(conn, stats):
    conn.executemany(
        "INSERT INTO key_stats(char, ema_delay_ms, timed_samples, attempts, errors) VALUES(?,?,?,?,?)"
        " ON CONFLICT(char) DO UPDATE SET"
        " ema_delay_ms = excluded.ema_delay_ms,"
        " timed_samples = excluded.timed_samples,"
        " attempts = excluded.attempts,"
        " errors = excluded.errors",
        [(s.char, s.ema_delay_ms, s.timed_samples, s.attempts, s.errors) for s in stats],
    )
    conn.commit()

# loads all per-key stats back so the trainer remembers you
def load_key_stats(conn):
    rows = conn.execute("SELECT char, ema_delay_ms, timed_samples, attempts, errors FROM key_stats").fetchall()
    return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]

# your last few rounds, newest first, for the little sparkline
def recent_sessions(conn, limit=10):
    return conn.execute(
        "SELECT id, started_at, wpm, accuracy, duration_s FROM sessions ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
