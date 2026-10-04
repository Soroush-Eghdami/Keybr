# letter unlocking like keybr: start small, earn new letters by getting fast
from dataclasses import dataclass, field

# most common english letters first, so unlocks feel natural
FREQUENCY_ORDER = list("etaoinshrdlucmfwypvbgkqjxz")
# you start with just these and earn the rest
STARTER_SET = list("enitrl")
TARGET_DELAY_MS = 340.0
MIN_SAMPLES = 20

@dataclass
class Progression:
    # letters youve unlocked so far plus what counts as fast enough
    unlocked: list = field(default_factory=lambda: list(STARTER_SET))
    target_delay_ms: float = TARGET_DELAY_MS
    min_samples: int = MIN_SAMPLES

    # the letters youre allowed to practice with right now
    @property
    def allowed(self):
        return set(self.unlocked)

    # the next letter waiting to be unlocked, none when youve got them all
    @property
    def next_locked(self):
        for ch in FREQUENCY_ORDER:
            if ch not in self.unlocked:
                return ch
        return None

    # tells if a letter is still locked, being learned, or fully mastered
    def key_status(self, char, ema_ms, samples):
        if char not in self.unlocked:
            return "locked"
        if samples >= self.min_samples and ema_ms <= self.target_delay_ms:
            return "mastered"
        return "learning"

    # True only when every unlocked letter is fast enough with enough practice
    def ready_to_unlock(self, stats):
        for ch in self.unlocked:
            ema, samples = stats.get(ch, (9999.0, 0))
            if samples < self.min_samples or ema > self.target_delay_ms:
                return False
        return True

    # unlocks the next letter if youve earned it, returns it so we can celebrate
    def maybe_unlock(self, stats):
        nxt = self.next_locked
        if nxt is None:
            return None
        if self.ready_to_unlock(stats):
            self.unlocked.append(nxt)
            return nxt
        return None
