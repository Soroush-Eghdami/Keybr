# builds practice text from real words and made-up ones
import logging
import random
from collections import Counter, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from importlib.resources import files as _res_files
except ImportError:  # python 3.8 fallback, not expected on 3.11+
    _res_files = None

# when the allowed pool is this small, real words get boring — use pseudowords
MIN_REAL_POOL = 15

# reads the word list file, falls back to a small builtin set if its missing
def load_words(path=None):
    if path is not None:
        p = Path(path)
        if p.exists():
            words = _read_word_file(p)
            if words:
                return words
        logger.warning("word list %s missing or empty, using builtin fallback", p)
        return list(_FALLBACK_WORDS)
    # packaged location: src/typetrainer/data/words_en.txt
    if _res_files is not None:
        try:
            data = _res_files("typetrainer.data").joinpath("words_en.txt").read_text(encoding="utf-8")
            words = [w.strip().lower() for w in data.splitlines()]
            words = [w for w in words if w.isalpha() and len(w) >= 2]
            if words:
                return words
        except (FileNotFoundError, ModuleNotFoundError) as exc:
            logger.warning("packaged word list missing (%s), using builtin fallback", exc)
            return list(_FALLBACK_WORDS)
    # legacy repo-root location (pre-5.5 layouts)
    legacy = Path(__file__).resolve().parents[3] / "data" / "words_en.txt"
    if legacy.exists():
        words = _read_word_file(legacy)
        if words:
            return words
    logger.warning("no word list found, using builtin fallback")
    return list(_FALLBACK_WORDS)


def _read_word_file(p):
    words = [w.strip().lower() for w in p.read_text(encoding="utf-8").splitlines()]
    return [w for w in words if w.isalpha() and len(w) >= 2]

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
# never returns a locked letter: the real-word pool is filtered by allowed,
# and pseudowords are generated under the same constraint
def generate_line(words, table=None, slow_keys=None, allowed=None, word_count=12, use_pseudo_ratio=0.35, rng=None):
    rng = rng or random.Random()
    slow_keys = slow_keys or set()
    pool = [w for w in words if allowed is None or all(c in allowed for c in w)]
    n_pseudo = round(word_count * use_pseudo_ratio) if table else 0
    n_real = word_count - n_pseudo
    if allowed is not None and table and 0 < len(pool) < MIN_REAL_POOL:
        # tiny pool (early unlock stages): mostly pseudowords, keep 2 real max
        n_real = min(n_real, 2)
        n_pseudo = word_count - n_real
    if not pool:
        n_real, n_pseudo = 0, word_count if table else 0
    real = pick_weighted_words(pool, slow_keys, n_real, rng) if n_real and pool else []
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
    if mixed:
        return " ".join(mixed)
    if pool:
        return " ".join(rng.choices(pool, k=word_count))
    return ""


_FALLBACK_WORDS = (
    "the quick brown fox jumps over lazy dog type speed focus rhythm "
    "practice makes perfect letters fingers keyboard trainer stats word "
    "about above after again below could every first found great house "
    "large learn never other place plant point right small sound spell "
    "still study their there these thing think three water where which world"
).split()
