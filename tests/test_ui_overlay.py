# regression test for: unlocked letter invisible in stats because frozen
# legacy stats for locked letters dominated every top-N list.
# Seeds a db the way pre-5.5 ungated code left it (full-alphabet stats),
# then asserts the overlay and summary only show unlocked letters.
import sqlite3

from typetrainer.storage import db
from typetrainer.ui.app import TrainerApp
from textual.widgets import Static


def _seed_legacy_db(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(db.SCHEMA)
    db._migrate(conn)
    conn.executemany(
        "INSERT INTO key_stats(char, ema_delay_ms, timed_samples, attempts, errors) VALUES(?,?,?,?,?)",
        [
            ("k", 891.0, 1, 1, 0),   # locked legacy junk
            ("h", 506.0, 8, 8, 5),   # locked legacy junk
            ("e", 250.0, 30, 30, 3),
            ("n", 300.0, 25, 25, 5),
            ("a", 141.0, 28, 28, 0),  # unlocked but fastest -> was buried
        ],
    )
    conn.execute("INSERT INTO meta(key, value) VALUES('unlocked', 'e,n,i,t,r,l,a')")
    conn.commit()
    conn.close()


def _hint(app):
    return str(app.query_one("#hint", Static).content)


async def _run():
    import tempfile
    tmp = tempfile.mktemp(suffix=".db")
    _seed_legacy_db(tmp)
    app = TrainerApp(db_path=tmp)
    async with app.run_test() as pilot:
        await pilot.pause()
        # stats overlay must list unlocked letters only
        await pilot.press("ctrl+s")
        await pilot.pause()
        overlay = _hint(app)
        before_unlocked = overlay.split("unlocked:")[0]
        assert "[bold]k[/]" not in before_unlocked, overlay
        assert "[bold]h[/]" not in before_unlocked, overlay
        for ch in "enitrla":
            assert ch in overlay, (ch, overlay)
        assert "unlocked: enitrla" in overlay
        # dismiss overlay, finish one round, summary must be unlocked-only too
        await pilot.press("ctrl+s")
        await pilot.pause()
        for ch in app.session.target:
            await pilot.press("space" if ch == " " else ch)
        await pilot.pause()
        summary = _hint(app)
        assert "done!" in summary, summary
        head = summary.split("recent WPM")[0]
        assert "[bold]k[/]" not in head and "[bold]h[/]" not in head, head


def test_overlay_and_summary_follow_unlocks():
    import asyncio
    asyncio.run(_run())
