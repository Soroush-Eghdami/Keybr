# builds practice text from real words and made-up ones
import random
from collections import Counter, defaultdict
from pathlib import Path

# reads the word list file, falls back to a small builtin set if its missing
def load_words(path):
    p = Path(path)
    if not p.exists():
        return list(_FALLBACK_WORDS)
    words = [w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines()]
    words = [w for w in words if w.isalpha() and len(w) >= 2]
    return words or list(_FALLBACK_WORDS)

# scores a word higher the more of your slow letters it contains
def word_weight(word, slow_keys, boost=3.0):
    hits = sum(1 for ch in word if ch in slow_keys)
    return 1.0 + min(hits, 4) * boost

# picks words with slow-letter words showing up more often
def pick_weighted_words(words, slow_keys, count, rng=None, boost=3.0):
    rng = rng or random.Random()
    weights = [word_weight(w, slow_keys, boost) for w in words]
    return rng.choices(words, weights=weights, k=count)

# learns which letters follow each other from the word list so fake words sound real
def build_ngram_table(words, n=2):
    table = defaultdict(Counter)
    pad = "^" * n
    for w in words:
        seq = pad + w + "$"
        for i in range(len(seq) - n):
            table[seq[i:i + n]][seq[i + n]] += 1
    return dict(table)

# grows one fake-but-pronounceable word, biased toward your weak letters
def generate_pseudoword(table, n=2, target_keys=None, allowed=None, max_len=8, rng=None, target_boost=4.0):
    rng = rng or random.Random()
    ctx = "^" * n
    out = []
    for _ in range(max_len + 4):
        opts = table.get(ctx)
        if not opts:
            break
        chars = list(opts.keys())
        weights = [float(opts[c]) for c in chars]
        if target_keys:
            for i, c in enumerate(chars):
                if c in target_keys:
                    weights[i] *= target_boost
        if allowed is not None:
            kept = [(c, w) for c, w in zip(chars, weights) if c == "$" or c in allowed]
            if not kept:
                break
            chars = [c for c, _ in kept]
            weights = [w for _, w in kept]
        nxt = rng.choices(chars, weights=weights, k=1)[0]
        if nxt == "$":
            if len(out) >= 2:
                break
            ctx = "^" * n
            continue
        out.append(nxt)
        ctx = (ctx + nxt)[-n:]
        if len(out) >= max_len:
            break
    word = "".join(out)
    if allowed is not None:
        word = "".join(c for c in word if c in allowed)
    return word[:max_len]

# mixes real words with some fake ones into one practice line
def generate_line(words, table=None, slow_keys=None, allowed=None, word_count=12, use_pseudo_ratio=0.35, rng=None):
    rng = rng or random.Random()
    slow_keys = slow_keys or set()
    pool = [w for w in words if allowed is None or all(c in allowed for c in w)]
    if not pool:
        pool = words
    n_pseudo = round(word_count * use_pseudo_ratio) if table else 0
    n_real = word_count - n_pseudo
    real = pick_weighted_words(pool, slow_keys, n_real, rng) if n_real else []
    pseudo = []
    if table and n_pseudo:
        tries = 0
        while len(pseudo) < n_pseudo and tries < n_pseudo * 3:
            tries += 1
            w = generate_pseudoword(table, target_keys=slow_keys, allowed=allowed, rng=rng)
            if len(w) >= 2:
                pseudo.append(w)
    mixed = real + pseudo
    rng.shuffle(mixed)
    return " ".join(mixed) if mixed else " ".join(rng.choices(pool, k=word_count))


_FALLBACK_WORDS = (
    "the quick brown fox jumps over lazy dog type speed focus rhythm "
    "practice makes perfect letters fingers keyboard trainer stats word "
    "about above after again below could every first found great house "
    "large learn never other place plant point right small sound spell "
    "still study their there these thing think three water where which world"
).split()
