# per-key average checks (Phase 5.5 locked rules)
from typetrainer.engine.stats import StatsTracker, update_ema

def test_ema_converges():
    ema = 500.0
    for _ in range(50):
        ema = update_ema(ema, 200.0, alpha=0.2)
    assert abs(ema - 200.0) < 5.0

def test_outliers_ignored_for_speed():
    t = StatsTracker()
    t.record("a", 300.0, True)
    before = t.stats["a"].ema_delay_ms
    t.record("a", 5000.0, True)
    assert t.stats["a"].ema_delay_ms == before
    assert t.stats["a"].timed_samples == 1
    assert t.stats["a"].attempts == 2

def test_outlier_on_first_sample_ignored():
    t = StatsTracker()
    t.record("a", 9000.0, True)
    st = t.stats["a"]
    assert st.timed_samples == 0
    assert st.attempts == 1
    assert st.ema_delay_ms == 400.0
    t.record("a", 250.0, True)
    assert st.ema_delay_ms == 250.0
    assert st.timed_samples == 1

def test_wrong_keystrokes_dont_touch_ema():
    t = StatsTracker()
    t.record("a", 200.0, True)
    before = t.stats["a"].ema_delay_ms
    t.record("a", 150.0, False)
    st = t.stats["a"]
    assert st.ema_delay_ms == before
    assert st.attempts == 2
    assert st.errors == 1
    assert st.error_rate == 0.5

def test_none_delay_never_updates_ema():
    t = StatsTracker()
    t.record("a", None, True)
    assert t.stats["a"].timed_samples == 0
    assert t.stats["a"].attempts == 1

def test_space_not_tracked():
    t = StatsTracker()
    assert t.record(" ", 100.0, True) is None
    assert " " not in t.stats

def test_slowest_keys_order():
    t = StatsTracker()
    t.record("a", 150.0, True)
    t.record("b", 600.0, True)
    assert t.slowest_keys(1)[0].char == "b"

def test_slowest_keys_allowed_filters_locked_legacy_stats():
    # frozen stats for locked letters (never re-sampled) must not top the lists
    t = StatsTracker()
    t.record("k", 891.0, True)  # locked legacy junk, 1 sample
    t.record("e", 300.0, True)
    t.record("a", 141.0, True)
    got = t.slowest_keys(5, allowed=set("enitrla"))
    assert [s.char for s in got] == ["e", "a"]
    assert all(s.char != "k" for s in got)

def test_error_prone_keys_allowed_filters_locked():
    t = StatsTracker()
    t.record("h", 200.0, False)  # locked, 100% error
    t.record("e", 200.0, False)
    t.record("e", 200.0, True)
    got = t.error_prone_keys(5, allowed=set("enitrla"))
    assert [s.char for s in got] == ["e"]

def test_load_rows_new_and_legacy():
    t = StatsTracker()
    t.load_rows([("a", 200.0, 5, 8, 2)])
    assert t.stats["a"].timed_samples == 5
    assert t.stats["a"].attempts == 8
    assert t.stats["a"].errors == 2
    t2 = StatsTracker()
    t2.load_rows([("b", 300.0, 10, 0.2)])
    assert t2.stats["b"].attempts == 10
    assert t2.stats["b"].timed_samples == 10
    assert t2.stats["b"].errors == 2
