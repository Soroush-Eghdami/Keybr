# one run of typing, holds the target text and where youre at
import time
from dataclasses import dataclass, field

# a single keypress with what you should have hit and what you hit
@dataclass
class Keystroke:
    expected: str
    typed: str
    delay_ms: float
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
        self.errors = []
        self._start = None
        self._last_time = None
        self._end = None

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
        if self._start is None:
            return 0.0
        end = self._end if self._end is not None else time.perf_counter()
        return max(0.0, end - self._start)

    # logs one typed char and moves the cursor, wrong chars still move on so you never get stuck
    def type_char(self, char, now=None):
        if self.finished:
            return None
        t = time.perf_counter() if now is None else now
        if self._start is None:
            self._start = t
            self._last_time = t
        delay_ms = max(0.0, (t - self._last_time) * 1000.0)
        self._last_time = t

        expected = self.target[self.position]
        correct = char == expected
        ks = Keystroke(expected, char, delay_ms, correct)
        ks.timestamp = t
        self.keystrokes.append(ks)
        self.errors.append(correct)
        self.position += 1

        if self.finished:
            self._end = t
        return ks

    # steps the cursor back one so you can retype it
    def backspace(self):
        if self.position <= 0:
            return False
        self.position -= 1
        if self.errors:
            self.errors.pop()
        self._end = None
        return True

    # builds the final wpm + accuracy numbers for this round
    def result(self):
        from .metrics import calc_accuracy, calc_wpm
        total = len(self.keystrokes)
        correct_keys = sum(1 for k in self.keystrokes if k.correct)
        correct_chars = sum(1 for ok in self.errors if ok)
        return SessionResult(
            calc_wpm(correct_chars, self.elapsed),
            calc_accuracy(correct_keys, total),
            correct_chars,
            total,
            self.elapsed,
        )

    # current wpm while the round is still going
    def live_wpm(self):
        from .metrics import calc_live_wpm
        correct_chars = sum(1 for ok in self.errors if ok)
        return calc_live_wpm(correct_chars, self.elapsed)
