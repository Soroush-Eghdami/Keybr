# per-key speed tracking using a running average
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# anything slower than this counts as a pause, not real typing speed
OUTLIER_MS = 2000.0
DEFAULT_ALPHA = 0.2
DEFAULT_EMA_MS = 400.0

# speed + mistake counts for one letter
# error_rate is a property (errors / attempts), never stored
@dataclass
class KeyStat:
    char: str
    ema_delay_ms: float = DEFAULT_EMA_MS
    timed_samples: int = 0
    attempts: int = 0
    errors: int = 0

    @property
    def samples(self):
        # deprecated alias: unlock gating and slow-key filters use timed_samples
        return self.timed_samples

    # share of presses on this key that were wrong
    @property
    def error_rate(self):
        if self.attempts == 0:
            return 0.0
        return self.errors / self.attempts


def _valid_delay(delay_ms):
    return delay_ms is not None and 0 <= delay_ms <= OUTLIER_MS

# blends the old average with the new delay so recent typing matters more
def update_ema(current, new_value, alpha=DEFAULT_ALPHA):
    return alpha * new_value + (1.0 - alpha) * current


class StatsTracker:
    # holds every keys stats in memory, saved to sqlite between runs
    def __init__(self, alpha=DEFAULT_ALPHA):
        self.alpha = alpha
        self.stats = {}

    # logs one keypress. Speed (EMA) updates only for correct keystrokes with
    # a valid (non-None, under-cap) delay — including a key's very first
    # sample. Wrong keystrokes only update attempts/errors. Spaces are ignored.
    def record(self, expected, delay_ms, correct):
        if expected == " ":
            return None
        st = self.stats.get(expected)
        if st is None:
            st = KeyStat(expected)
            self.stats[expected] = st
        st.attempts += 1
        if not correct:
            st.errors += 1
            return st
        if not _valid_delay(delay_ms):
            return st
        if st.timed_samples == 0:
            st.ema_delay_ms = float(delay_ms)
        else:
            st.ema_delay_ms = update_ema(st.ema_delay_ms, float(delay_ms), self.alpha)
        st.timed_samples += 1
        return st

    # your n slowest letters by average delay (needs timed samples first)
    # allowed optionally restricts to unlocked letters so frozen legacy
    # stats for locked letters (which can never be re-sampled) don't
    # dominate the list forever
    def slowest_keys(self, n=5, allowed=None):
        vals = self.stats.values()
        if allowed is not None:
            vals = [s for s in vals if s.char in allowed]
        return sorted(vals, key=lambda s: s.ema_delay_ms, reverse=True)[:n]

    # your n most mistake-prone letters by error rate
    def error_prone_keys(self, n=5, allowed=None):
        vals = self.stats.values()
        if allowed is not None:
            vals = [s for s in vals if s.char in allowed]
        return sorted(vals, key=lambda s: (s.error_rate, s.attempts), reverse=True)[:n]

    # flattens stats into rows so sqlite can store them (counts, not rates)
    def to_rows(self):
        return [(s.char, s.ema_delay_ms, s.timed_samples, s.attempts, s.errors) for s in self.stats.values()]

    # rebuilds stats from rows. Accepts new 5-tuples and legacy 4-tuples
    # (char, ema, samples, error_rate) from before Phase 5.5.
    def load_rows(self, rows):
        for row in rows:
            if len(row) == 5:
                char, ema, timed, attempts, errors = row
                self.stats[char] = KeyStat(char, float(ema), int(timed), int(attempts), int(errors))
            elif len(row) == 4:
                char, ema, samples, err_rate = row
                samples = int(samples)
                errors = int(round(float(err_rate) * samples))
                self.stats[char] = KeyStat(char, float(ema), samples, samples, errors)
            else:
                logger.warning("skipping malformed key stat row: %r", row)
