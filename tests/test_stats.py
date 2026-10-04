# per-key average checks
from typetrainer.engine.stats import StatsTracker, update_ema

def test_ema_converges():
    # feeding the same delay over and over pulls the average right to it
    ema = 500.0
    for _ in range(50):
        ema = update_ema(ema, 200.0, alpha=0.2)
    assert abs(ema - 200.0) < 5.0

def test_outliers_ignored_for_speed():
    # a 5 second pause is you thinking, it must not wreck the speed average
    t = StatsTracker()
    t.record("a", 300.0, True)
    before = t.stats["a"].ema_delay_ms
    t.record("a", 5000.0, True)
    assert t.stats["a"].ema_delay_ms == before

def test_slowest_keys_order():
    # the key with the bigger average delay comes out on top
    t = StatsTracker()
    t.record("a", 150.0, True)
    t.record("b", 600.0, True)
    assert t.slowest_keys(1)[0].char == "b"
