# session state machine: backspace, finishing, None delays, replay parity
from typetrainer.engine.session import Session, replay

def test_first_keystroke_delay_is_none():
    s = Session("hi")
    ks = s.type_char("h", now=100.0)
    assert ks.delay_ms is None
    ks2 = s.type_char("i", now=100.2)
    assert abs(ks2.delay_ms - 200.0) < 1e-6

def test_keystroke_after_backspace_is_none():
    s = Session("hi")
    s.type_char("h", now=0.0)
    s.type_char("x", now=0.2)
    assert s.backspace() is True
    ks = s.type_char("i", now=1.5)
    assert ks.delay_ms is None

def test_backspace_at_start_returns_false():
    assert Session("hi").backspace() is False

def test_finish_and_result():
    s = Session("ab")
    s.type_char("a", now=0.0)
    s.type_char("b", now=0.4)
    assert s.finished is True
    res = s.result()
    assert res.total_keystrokes == 2
    assert res.correct_chars == 2
    assert res.accuracy == 100.0

def test_correct_flags_rename():
    s = Session("ab")
    s.type_char("a", now=0.0)
    s.type_char("x", now=0.1)
    assert s.correct_flags == [True, False]
    assert s.errors == s.correct_flags

def test_replay_matches_live():
    target = "hello"
    s = Session(target)
    t = 10.0
    delays = [None, 0.18, 0.22, 0.19, 0.25]
    for ch, d in zip(target, delays):
        if d is None:
            s.type_char(ch, now=t)
        else:
            t += d
            s.type_char(ch, now=t)
    live = s.result(now=t)
    events = [{"key": ch, "delay_ms": (None if d is None else d * 1000.0)} for ch, d in zip(target, delays)]
    rs, rres = replay(target, events)
    assert rres.wpm == live.wpm or abs(rres.wpm - live.wpm) < 1e-9
    assert rres.accuracy == live.accuracy
    assert rres.total_keystrokes == live.total_keystrokes

def test_replay_with_backspace():
    target = "hi"
    events = [
        {"key": "h", "delay_ms": None},
        {"key": "x", "delay_ms": 200.0},
        {"key": "Backspace", "delay_ms": 300.0},
        {"key": "i", "delay_ms": 500.0},
    ]
    s, res = replay(target, events)
    assert s.finished is True
    assert res.total_keystrokes == 3
    # h correct, x wrong, i correct → 2/3
    assert abs(res.accuracy - 200.0 / 3.0) < 1e-6
    # keystroke after backspace carries no timing
    assert s.keystrokes[-1].delay_ms is None
