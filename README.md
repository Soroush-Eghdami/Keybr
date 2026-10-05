<div align="center">

# ⌨️ keybr

### *the terminal typing trainer that learns your weak keys*

![Python](https://img.shields.io/badge/python-3.11%2B-58a6ff?style=for-the-badge&logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/TUI-Textual-3fb950?style=for-the-badge)
![SQLite](https://img.shields.io/badge/stats-SQLite-d29922?style=for-the-badge)
![No ML](https://img.shields.io/badge/brain-just_stats-f85149?style=for-the-badge)

*No AI. No fluff. Just per-key statistics that hunt down your slowest letters — then force you to practice them.*

</div>

---

## ✨ What is this?

**keybr** is a [keybr.com](https://www.keybr.com)-style typing trainer that lives in your terminal. It measures the speed of **every individual key you press**, builds a statistical profile of your fingers, then generates practice text weighted toward your weakest letters.

Type. It watches. It adapts. You get faster.

```
┌──────────────────────────────────────────────────────────────┐
│ ⌨  keybr  ·  adaptive typing trainer                         │
│  [ WPM  42 ]   [ ACC  96% ]   [ TIME  18s ]                   │
│                                                              │
│  ╭─ TYPE THE LINE BELOW ───────────────────────────────╮     │
│  │  the quick brown fox jumps over…                    │     │
│  │  ████▁▁▁▁▁▁▁▁▁▁▁▁  ← your glowing caret            │     │
│  ╰─────────────────────────────────────────────────────╯     │
│                                                              │
│   Q  W  E  R  T  Y  U  I  O  P                               │
│     A  S  D  F  G  H  J  K  L                                │
│          Z  X  C  V  B  N  M                                 │
│   🟩 fast   🟨 ok   🟥 slow   🟦 next key                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

> Requires **Python 3.11+**. Everything runs inside the existing `venv`.

```bash
git clone https://github.com/Soroush-Eghdami/Keybr.git

cd Keybr

python -m venv venv

# Windows: .\venv\Scripts\Activate.ps1   |   Linux/macOS: source venv/bin/activate

pip install -e .

typetrainer
```

### Controls

| Key | Action |
|-----|--------|
| `a–z`, `space` | type |
| `backspace` | fix a mistake |
| `tab` / `ctrl+r` | fresh line |
| `ctrl+s` | stats overlay (slowest keys, unlock progress) |
| `ctrl+q` | quit |

---

## 🧠 How it works

```
  you type ──▶ Session ──▶ Keystroke(delay, correct?)
                                │
                                ▼
                    StatsTracker (EMA per key)
                     ema = α·new + (1−α)·old   α ≈ 0.2
                     pauses > 2000 ms are ignored
                                │
                                ▼
              Generator (weighted words + n-gram pseudowords)
                                │
                                ▼
              Progression (unlock e→t→a→… as you hit 340ms/key)
                                │
                                ▼
                        SQLite (~/.typetrainer/trainer.db)
```

| Module | Job |
|--------|-----|
| `engine/session.py` | state machine — timer starts on first keystroke |
| `engine/metrics.py` | `WPM = (chars/5)/min`, accuracy = correct/total |
| `engine/stats.py` | per-key EMA speed + error rate |
| `engine/generator.py` | Markov (n-gram) pseudo-words biased to weak keys |
| `engine/progression.py` | keybr-style letter unlocking |
| `storage/` | SQLite: sessions, keystrokes, key stats |
| `ui/` | Textual TUI — **the only place Textual is imported** |

> **Design rule:** `engine/` never imports the UI. Swap Textual for a GUI or web frontend later without touching a line of logic.

---

## 📁 Layout

```
keybr/
├── data/words_en.txt            # 349-word training corpus
├── src/typetrainer/
│   ├── engine/                  # pure logic (session, metrics, stats,
│   │                            #          generator, progression)
│   ├── storage/                 # sqlite connection + repository
│   └── ui/                      # Textual app + widgets (theme lives here)
├── tests/                       # pytest — engine only, no UI
├── pyproject.toml
└── README.md
```

---

## 🧪 Tests

```powershell
pytest -q
# 10 passed
```

Engine logic is tested with fake keystroke data — no manual typing required.

---

## 🗺️ Roadmap

- [x] **Phase 0** — repo, venv, Textual hello
- [x] **Phase 1** — MVP typing loop + WPM/accuracy
- [x] **Phase 2** — per-key stats + SQLite
- [x] **Phase 3** — smart generator (weighted words + n-grams)
- [x] **Phase 4** — letter unlocking
- [x] **Phase 5** — heatmap keyboard, live pills, session summary
- [ ] **Phase 6** — settings screen, TOML config, CSV export
- [ ] **Phase 7** — full backend support for a web frontend
- [ ] Stretch — ghost racing, code-typing mode, Dvorak/Colemak

---

<div align="center">

*built for people who want to feel their fingers get smarter.*

**type badly. practice honestly. unlock letters. 🔓**

</div>
