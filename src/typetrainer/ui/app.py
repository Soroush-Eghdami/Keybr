# the actual terminal app, wires the engine + sqlite + screen together
import random
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.widgets import Footer, Static
from textual import events
from ..engine.generator import build_ngram_table, generate_line, load_words
from ..engine.metrics import calc_accuracy
from ..engine.session import Session
from ..engine.stats import StatsTracker
from ..engine.progression import Progression
from ..storage.db import get_connection, get_meta, set_meta
from ..storage.repository import load_key_stats, recent_sessions, save_session, upsert_key_stats
from .widgets import KeyboardHeatmap, StatPill, TypingDisplay

APP_CSS = """
Screen {
    background: #0d1117;
    color: #e6edf3;
}
#topbar {
    height: 3;
    background: #010409;
    border-bottom: tall #21262d;
    padding: 0 2;
}
#logo {
    color: #58a6ff;
    text-style: bold;
    width: auto;
    padding-top: 1;
}
#pills {
    width: auto;
    height: 3;
    padding-top: 1;
}
StatPill {
    width: auto;
    margin-right: 1;
}
#main {
    align: center middle;
    padding: 1 2;
}
#card {
    width: 92;
    max-width: 92;
    background: #161b22;
    border: round #30363d;
    padding: 2 3;
}
#card-title {
    color: #8b949e;
    text-style: bold;
    margin-bottom: 1;
}
#typing-wrap {
    background: #0d1117;
    border: round #21262d;
    padding: 2 2;
    height: auto;
    min-height: 5;
}
TypingDisplay {
    height: auto;
}
#hint {
    color: #6e7681;
    margin-top: 1;
}
#keyboard-wrap {
    margin-top: 1;
    background: #010409;
    border: round #21262d;
    padding: 1 2;
    height: auto;
}
KeyboardHeatmap {
    height: auto;
}
Footer {
    background: #010409;
}
"""

DATA_WORDS = Path(__file__).resolve().parents[3] / "data" / "words_en.txt"


class TrainerApp(App):
    CSS = APP_CSS
    TITLE = "keybr — adaptive typing trainer"

    BINDINGS = [
        ("tab", "restart", "restart"),
        ("ctrl+s", "toggle_stats", "stats"),
        ("ctrl+r", "restart", "restart"),
    ]

    def __init__(self, words_file=None, db_path=None):
        super().__init__()
        self.words = load_words(words_file or DATA_WORDS)
        self.table = build_ngram_table(self.words, n=2)
        self.conn = get_connection(db_path)
        self.tracker = StatsTracker()
        self.tracker.load_rows(load_key_stats(self.conn))
        self.progression = Progression()
        saved = get_meta(self.conn, "unlocked", "")
        if saved:
            chars = [c for c in saved.split(",") if c.isalpha()]
            if chars:
                self.progression.unlocked = chars
        self.rng = random.Random()
        self.session = Session("")
        self.showing_stats = False

    # lays out the top bar, typing card and keyboard
    def compose(self) -> ComposeResult:
        with Vertical(id="topbar"):
            with Horizontal():
                yield Static("⌨  keybr  ·  adaptive typing trainer", id="logo")
                with Horizontal(id="pills"):
                    yield StatPill("WPM", "0", "#3fb950", id="pill-wpm")
                    yield StatPill("ACC", "100%", "#58a6ff", id="pill-acc")
                    yield StatPill("TIME", "0s", "#d29922", id="pill-time")
        with Center(id="main"):
            with Vertical(id="card"):
                yield Static("TYPE THE LINE BELOW  ·  tab = new line", id="card-title")
                with Vertical(id="typing-wrap"):
                    yield TypingDisplay(id="typing")
                yield Static("", id="hint")
                with Vertical(id="keyboard-wrap"):
                    yield KeyboardHeatmap(id="keyboard")
        yield Footer()

    # starts the live timer tick and deals the first line
    def on_mount(self):
        self.set_interval(0.1, self._refresh_live)
        self.new_round()

    # your worst letters, only counting ones youve actually typed a bit
    def _slow_keys(self, n=6):
        return {s.char for s in self.tracker.slowest_keys(n) if s.samples >= 3}

    # deals a fresh line biased toward your slow letters and resets the round
    def new_round(self, word_count=12):
        slow = self._slow_keys()
        target = generate_line(self.words, self.table, slow_keys=slow, word_count=word_count, rng=self.rng)
        self.session = Session(target)
        self.showing_stats = False
        typing = self.query_one("#typing", TypingDisplay)
        typing.target = target
        typing.typed_ok = ()
        typing.cursor = 0
        self._paint_keyboard()
        self.query_one("#hint", Static).update("start typing — timer begins on your first keystroke")

    # handles every keypress: typing, backspace, restart and stats shortcuts
    async def on_key(self, event: events.Key):
        if event.key in ("tab", "ctrl+r"):
            event.prevent_default()
            self.new_round()
            return
        if event.key == "ctrl+s":
            event.prevent_default()
            self.toggle_stats_view()
            return
        if self.showing_stats:
            if event.key in ("enter", "space", "escape"):
                self.new_round()
            return
        if event.key == "backspace":
            if self.session.backspace():
                self._sync_typing()
            event.prevent_default()
            return
        if event.is_printable and len(event.character or "") == 1:
            ch = event.character or ""
            if ch == "\r":
                return
            self.session.type_char(ch)
            self._sync_typing()
            if self.session.finished:
                self.finish_round()
            event.prevent_default()

    # repaints the typed colors and moves the blue next-key highlight
    def _sync_typing(self):
        typing = self.query_one("#typing", TypingDisplay)
        typing.typed_ok = tuple(self.session.errors)
        typing.cursor = self.session.position
        nxt = self.session.target[self.session.position] if not self.session.finished else ""
        self.query_one("#keyboard", KeyboardHeatmap).next_key = nxt.lower()

    # refreshes the WPM / ACC / TIME pills 10x a second while you type
    def _refresh_live(self):
        if self.showing_stats or not self.session.started:
            return
        wpm = self.session.live_wpm()
        total = len(self.session.keystrokes)
        correct = sum(1 for k in self.session.keystrokes if k.correct)
        try:
            self.query_one("#pill-wpm", StatPill).update(f"{wpm:.0f}")
            self.query_one("#pill-acc", StatPill).update(f"{calc_accuracy(correct, total):.0f}%")
            self.query_one("#pill-time", StatPill).update(f"{self.session.elapsed:.0f}s")
        except Exception:
            pass

    # saves the round, updates your key averages and maybe unlocks a letter
    def finish_round(self):
        res = self.session.result()
        for k in self.session.keystrokes:
            if k.expected != " ":
                self.tracker.record(k.expected, k.delay_ms, k.correct)
        upsert_key_stats(self.conn, list(self.tracker.stats.values()))
        try:
            save_session(self.conn, res, self.session.keystrokes)
        except Exception:
            pass
        stat_map = {c: (s.ema_delay_ms, s.samples) for c, s in self.tracker.stats.items()}
        unlocked = self.progression.maybe_unlock(stat_map)
        if unlocked:
            set_meta(self.conn, "unlocked", ",".join(self.progression.unlocked))
        self._paint_keyboard()
        self.show_summary(res, just_unlocked=unlocked)

    # recolors the keyboard from your current speed stats
    def _paint_keyboard(self):
        kb = self.query_one("#keyboard", KeyboardHeatmap)
        kb.emas = {c: s.ema_delay_ms for c, s in self.tracker.stats.items()}
        kb.next_key = self.session.target[0].lower() if self.session.target else ""

    # end-of-round report with wpm, worst keys and the recent-history sparkline
    def show_summary(self, res, just_unlocked=None):
        self.showing_stats = True
        slow = self.tracker.slowest_keys(5)
        bad = self.tracker.error_prone_keys(5)
        hist = recent_sessions(self.conn, 8)
        spark = _sparkline([h[2] for h in reversed(hist)]) if hist else "—"

        def fmt(keys):
            if not keys:
                return "  (type more to build stats)"
            return "\n".join(f"   [bold]{s.char}[/]  {s.ema_delay_ms:4.0f}ms   err {s.error_rate*100:4.1f}%  n={s.samples}" for s in keys)

        unlock_msg = f"\n🔓 [bold green]NEW LETTER UNLOCKED: {just_unlocked}[/]" if just_unlocked else ""
        self.query_one("#hint", Static).update(
            f"[bold green]done![/]  WPM [bold]{res.wpm:.0f}[/]  ·  acc [bold]{res.accuracy:.1f}%[/]  ·  {res.elapsed_seconds:.1f}s{unlock_msg}\n"
            f"[dim]slowest keys:[/]\n{fmt(slow)}\n"
            f"[dim]most errors:[/]\n{fmt(bad)}\n"
            f"[dim]recent WPM {spark}[/]\n"
            f"[dim]tab = next line  ·  ctrl+s = stats[/]"
        )

    # flips between the typing line and your full key stats overlay
    def toggle_stats_view(self):
        self.showing_stats = not self.showing_stats
        hint = self.query_one("#hint", Static)
        if self.showing_stats:
            lines = ["[bold cyan]⌨ your keys[/]  (green=fast red=slow)"]
            for s in self.tracker.slowest_keys(8):
                st = self.progression.key_status(s.char, s.ema_delay_ms, s.samples)
                lines.append(f"  [bold]{s.char}[/] {s.ema_delay_ms:4.0f}ms  err {s.error_rate*100:4.1f}%  {st}")
            lines.append(f"\nunlocked: {''.join(self.progression.unlocked)}   next: {self.progression.next_locked or '— all done!'}")
            lines.append("\n[dim]press ctrl+s or tab to go back[/]")
            hint.update("\n".join(lines))
        else:
            self._sync_typing()
            hint.update("start typing — timer begins on your first keystroke")

    # tab shortcut: throw this line away and deal a new one
    def action_restart(self):
        self.new_round()

    # ctrl+s shortcut: same as the stats toggle
    def action_toggle_stats(self):
        self.toggle_stats_view()

# turns a list of wpm numbers into a tiny ▁▂▃ bar chart
def _sparkline(values):
    blocks = "▁▂▃▄▅▆▇█"
    if not values:
        return "—"
    lo, hi = min(values), max(values)
    if hi - lo < 1e-6:
        return "▅" * len(values)
    return "".join(blocks[int((v - lo) / (hi - lo) * 7)] for v in values)

# launches the app when you run typetrainer
def main():
    TrainerApp().run()


if __name__ == "__main__":
    main()
