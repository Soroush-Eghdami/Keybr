# progression unlocks on timed samples, not attempts
from typetrainer.engine.progression import Progression

def _stats_for(unlocked, ema=200.0, timed=25):
    return {ch: (ema, timed) for ch in unlocked}

def test_unlock_needs_all_keys_fast_with_timed_samples():
    p = Progression()
    assert p.maybe_unlock(_stats_for(p.unlocked)) == p.unlocked[-1]
    assert len(p.unlocked) == 7

def test_no_unlock_when_slow():
    p = Progression()
    stats = _stats_for(p.unlocked)
    stats[p.unlocked[0]] = (900.0, 50)
    assert p.maybe_unlock(stats) is None

def test_no_unlock_on_attempts_without_timed_samples():
    p = Progression()
    # plenty of attempts in spirit, but timed gating uses timed count
    stats = {ch: (200.0, 3) for ch in p.unlocked}
    assert p.ready_to_unlock(stats) is False

def test_key_status():
    p = Progression()
    assert p.key_status("z", 100.0, 50) == "locked"
    ch = p.unlocked[0]
    assert p.key_status(ch, 200.0, 25) == "mastered"
    assert p.key_status(ch, 900.0, 25) == "learning"
    assert p.key_status(ch, 200.0, 2) == "learning"
