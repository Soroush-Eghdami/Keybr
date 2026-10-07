# shared fixtures: same file the future JS test will run
import json
from pathlib import Path
from typetrainer.engine.session import replay

def test_shared_fixtures_replay_deterministically():
    data = json.loads(Path(__file__).parent.joinpath("fixtures", "sessions.json").read_text(encoding="utf-8"))
    assert len(data) >= 2
    for case in data:
        s1, r1 = replay(case["target"], case["events"])
        s2, r2 = replay(case["target"], case["events"])
        assert (r1.wpm, r1.accuracy, r1.total_keystrokes) == (r2.wpm, r2.accuracy, r2.total_keystrokes)
    clean = next(c for c in data if c["name"] == "clean line")
    _, res = replay(clean["target"], clean["events"])
    assert res.accuracy == 100.0
    assert res.total_keystrokes == len(clean["target"])
    fixed = next(c for c in data if c["name"] == "with error and backspace")
    _, res2 = replay(fixed["target"], fixed["events"])
    assert abs(res2.accuracy - 200.0 / 3.0) < 1e-6
