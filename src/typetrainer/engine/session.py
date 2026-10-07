# one run of typing, holds the target text and where youre at
import time
from dataclasses import dataclass, field
from typing import Optional

BACKSPACE = "Backspace"

# a single keypress with what you should have hit and what you hit
# delay_ms is None when there is no valid timing (first keystroke of a line,
# or the keystroke immediately after a Backspace — that gap is recovery time)
@dataclass
class Keystroke:
    expected: str
    typed: str
    delay_ms: Optional[float]
    correct: bool
    timestamp: float = field(default_factory=time.perf_counter)

# final numbers shown when a round ends
@dataclass
class SessionResult:
    wpm: float
    accuracy: float
    correct_chars: int
    total_keystrokes: int
    elapsed_seconds: float


class Session:
    # timer starts on your first keypress, backspace steps back one char
    def __init__(self, target):
        self.target = target
        self.position = 0
        self.keystrokes = []
        self.correct_flags = []
        self._start = None
        self._last_time = None
        self._end = None

    @property
    def errors(self):
        # deprecated alias for correct_flags (True = correct)
        return self.correct_flags

    # True once youve pressed the first key
    @property
    def started(self):
        return self._start is not None

    # True once youve reached the end of the target text
    @property
    def finished(self):
        return self.position >= len(self.target)

    # seconds since first keypress, freezes when the round ends
    @property
    def elapsed(self):
        return self.elapsed_at()

    def elapsed_at(self, now=None):
        if self._start is None:
            return 0.0
        if self._end is not None:
            return max(0.0, self._end - self._start)
        if now is None:
            now = time.perf_counter()
        return max(0.0, now - self._start)

    # logs one typed char and moves the cursor, wrong chars still move on so you never get stuck
    def type_char(self, char, now=None):
        if self.finished:
            return None
        t = time.perf_counter() if now is None else now
        if self._start is None:
            self._start = t
            delay_ms = None
        elif self._last_time is None:
            # keystroke immediately after a backspace: recovery time, not typing time
            delay_ms = None
        else:
            delay_ms = max(0.0, (t - self._last_time) * 1000.0)
        self._last_time = t

        expected = self.target[self.position]
        correct = char == expected
        ks = Keystroke(expected, char, delay_ms, correct)
        ks.timestamp = t
        self.keystrokes.append(ks)
        self.correct_flags.append(correct)
        self.position += 1

        if self.finished:
            self._end = t
        return ks

    # steps the cursor back one so you can retype it
    def backspace(self):
        if self.position <= 0:
            return False
        self.position -= 1
        if self.correct_flags:
            self.correct_flags.pop()
        self._last_time = None
        self._end = None
        return True

    # builds the final wpm + accuracy numbers for this round
    def result(self, now=None):
        from .metrics import calc_accuracy, calc_wpm
        total = len(self.keystrokes)
        correct_keys = sum(1 for k in self.keystrokes if k.correct)
        correct_chars = sum(1 for ok in self.correct_flags if ok)
        return SessionResult(
            calc_wpm(correct_chars, self.elapsed_at(now)),
            calc_accuracy(correct_keys, total),
            correct_chars,
            total,
            self.elapsed_at(now),
        )

    # current wpm while the round is still going
    def live_wpm(self):
        from .metrics import calc_live_wpm
        correct_chars = sum(1 for ok in self.correct_flags if ok)
        return calc_live_wpm(correct_chars, self.elapsed)


def replay(target, events):
    """Replay a line through the same Session state machine with a synthetic clock.

    events: list of {"key": str, "delay_ms": float | None}. The first event
    must have delay_ms None; later events carry ms since the previous event.
    "Backspace" events move the cursor back. Backspace events themselves are
    never counted toward attempts — only typed keys are.
    Returns (session, result) where result is frozen on the synthetic clock.
    """
    session = Session(target)
    t = 0.0
    for i, ev in enumerate(events):
        key = ev["key"] if isinstance(ev, dict) else ev[0]
        delay = ev["delay_ms"] if isinstance(ev, dict) else ev[1]
        if i == 0:
            t = 0.0
        elif delay is not None:
            t += delay / 1000.0
        if key == BACKSPACE:
            session.backspace()
            # advance the last-time marker so the clock keeps moving; the
            # next type_char still records delay None (recovery time)
            continue
        session.type_char(key, now=t)
    if not session.finished:
        session._end = t
    return session, session.result(now=t)
