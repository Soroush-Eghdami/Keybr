# TOML-backed settings. These same fields later become Django Profile fields.
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path.home() / ".typetrainer" / "config.toml"

@dataclass
class Settings:
    words_per_test: int = 12
    target_delay_ms: float = 340.0
    min_samples: int = 20
    alpha: float = 0.2

def load_settings(path=None):
    p = Path(path) if path else DEFAULT_PATH
    s = Settings()
    if not p.exists():
        return s
    try:
        import tomllib
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("ignoring corrupt config %s: %s", p, exc)
        return s
    for key in asdict(s):
        if key in data:
            try:
                setattr(s, key, type(getattr(s, key))(data[key]))
            except (TypeError, ValueError):
                logger.warning("ignoring bad config value %r=%r", key, data[key])
    return s

def save_settings(settings, path=None):
    p = Path(path) if path else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# keybr settings — words_per_test, target_delay_ms, min_samples, alpha"]
    for key, value in asdict(settings).items():
        lines.append(f"{key} = {value!r}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
