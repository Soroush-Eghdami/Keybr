# per-key speed tracking using a running average
from dataclasses import dataclass

# anything slower than this counts as a pause, not real typing speed
OUTLIER_MS = 2000.0
DEFAULT_ALPHA = 0.2

# speed + mistake count for one letter
@dataclass
class KeyStat:
    char: str
    ema_delay_ms: float = 400.0
    samples: int = 0
    errors: int = 0

    # share of presses on this key that were wrong
    @property
    def error_rate(self):
        if self.samples == 0:
            return 0.0
        return self.errors / self.samples

# blends the old average with the new delay so recent typing matters more
def update_ema(current, new_value, alpha=DEFAULT_ALPHA):
    return alpha * new_value + (1.0 - alpha) * current


class StatsTracker:
    # holds every keys stats in memory, saved to sqlite between runs
    def __init__(self, alpha=DEFAULT_ALPHA):
        self.alpha = alpha
        self.stats = {}

    # logs one keypress, pauses dont touch the speed average but still count mistakes
    def record(self, expected, delay_ms, correct):
        st = self.stats.get(expected)
        if st is None:
            st = KeyStat(expected, delay_ms, 1, 0 if correct else 1)
            self.stats[expected] = st
            return st
        if delay_ms <= OUTLIER_MS and delay_ms >= 0:
            st.ema_delay_ms = update_ema(st.ema_delay_ms, delay_ms, self.alpha)
        st.samples += 1
        if not correct:
            st.errors += 1
        return st

    # your n slowest letters by average delay
    def slowest_keys(self, n=5):
        return sorted(self.stats.values(), key=lambda s: s.ema_delay_ms, reverse=True)[:n]

    # your n most mistake-prone letters by error rate
    def error_prone_keys(self, n=5):
        return sorted(self.stats.values(), key=lambda s: (s.error_rate, s.samples), reverse=True)[:n]

    # flattens stats into rows so sqlite can store them
    def to_rows(self):
        return [(s.char, s.ema_delay_ms, s.samples, s.error_rate) for s in self.stats.values()]

    # rebuilds stats back from sqlite rows
    def load_rows(self, rows):
        for char, ema, samples, err_rate in rows:
            self.stats[char] = KeyStat(char, ema, samples, round(err_rate * samples))
