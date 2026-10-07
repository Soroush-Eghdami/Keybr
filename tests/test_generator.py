# word generator checks
import random
from typetrainer.engine.generator import build_ngram_table, generate_line, generate_pseudoword, pick_weighted_words
from typetrainer.engine.progression import STARTER_SET

WORDS = ["apple", "berry", "cherry", "elder", "thorn", "zebra"]

def test_weighted_words_bias_to_slow_keys():
    # words with your slow letter in them should get picked way more
    rng = random.Random(0)
    picks = pick_weighted_words(WORDS, {"z"}, 500, rng=rng)
    z_rate = sum(1 for w in picks if "z" in w) / len(picks)
    assert z_rate > 0.3

def test_pseudo_only_allowed_letters():
    # fake words must never sneak in letters you havent unlocked yet
    table = build_ngram_table(WORDS, n=2)
    rng = random.Random(1)
    for _ in range(50):
        w = generate_pseudoword(table, target_keys={"e"}, allowed=set("abertychlz"), rng=rng)
        assert all(c in "abertychlz" for c in w)

def test_generate_line_word_count():
    # asking for 8 words gives back exactly 8 words
    table = build_ngram_table(WORDS, n=2)
    line = generate_line(WORDS, table, slow_keys={"e"}, word_count=8, rng=random.Random(2))
    assert len(line.split()) == 8

def test_generate_line_never_leaks_locked_letters():
    from typetrainer.engine.generator import load_words
    words = load_words()
    table = build_ngram_table(words, n=2)
    allowed = set(STARTER_SET)
    for seed in range(100):
        line = generate_line(words, table, slow_keys=set("et"), allowed=allowed, rng=random.Random(seed))
        nospace = line.replace(" ", "")
        assert nospace, seed
        assert all(c in allowed for c in nospace), (seed, line)
