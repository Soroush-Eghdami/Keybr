# wpm + accuracy checks
from typetrainer.engine.metrics import calc_accuracy, calc_live_wpm, calc_wpm

def test_wpm_basic():
    # 60 correct chars in a minute is 12 wpm by definition
    assert calc_wpm(60, 60.0) == 12.0

def test_wpm_zero():
    # nothing typed or no time passed means 0 wpm, never crash
    assert calc_wpm(0, 10.0) == 0.0
    assert calc_wpm(50, 0.0) == 0.0

def test_accuracy():
    # 90 out of 100 right is 90 percent, empty round counts as perfect
    assert calc_accuracy(90, 100) == 90.0
    assert calc_accuracy(0, 0) == 100.0

def test_live_wpm_cold_start():
    # first split second of typing always shows 0 so the number doesnt spike
    assert calc_live_wpm(10, 0.2) == 0.0
