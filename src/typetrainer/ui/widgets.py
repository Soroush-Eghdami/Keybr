# custom widgets for the typing screen
from rich.text import Text
from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive
from rich.console import RenderableType


class TypingDisplay(Static):
    # the big line you type, green = right, red = wrong, blue block = where you are
    target: reactive[str] = reactive("")
    typed_ok: reactive[tuple] = reactive(())
    cursor: reactive[int] = reactive(0)

    def render(self) -> RenderableType:
        t = self.target or ""
        ok = self.typed_ok or ()
        txt = Text()
        for i, ch in enumerate(t):
            if i < len(ok):
                if ok[i]:
                    txt.append(ch, style="bold #3fb950 on #0d1117")
                else:
                    txt.append(ch, style="bold #f85149 on #3d0a0a underline")
            elif i == self.cursor:
                if ch == " ":
                    txt.append("▁", style="bold black on #58a6ff")
                else:
                    txt.append(ch, style="bold black on #58a6ff")
            else:
                txt.append(ch, style="dim #8b949e")
        return txt


class StatPill(Static):
    # little badge in the top bar like WPM 42
    def __init__(self, label, value, accent, **kwargs):
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._accent = accent

    def update(self, value):
        self._value = value
        self.refresh()

    def render(self) -> RenderableType:
        t = Text()
        t.append(f" {self._label} ", style=f"black on {self._accent}")
        t.append(f" {self._value} ", style=f"bold {self._accent} on #161b22")
        return t


KEYBOARD_ROWS = [
    list("qwertyuiop"),
    list("asdfghjkl"),
    list("zxcvbnm"),
]

# picks the key color by speed: green fast, amber ok, red slow, grey = no data yet
def heat_color(ema_ms):
    if ema_ms is None:
        return "#30363d"
    if ema_ms < 250:
        return "#3fb950"
    if ema_ms < 350:
        return "#d29922"
    if ema_ms < 500:
        return "#db6d28"
    return "#f85149"


class KeyboardHeatmap(Widget):
    # mini keyboard at the bottom, colors show speed and blue marks the next key
    emas: reactive[dict] = reactive({})
    next_key: reactive[str] = reactive("")

    def render(self) -> RenderableType:
        t = Text(justify="center")
        for r, row in enumerate(KEYBOARD_ROWS):
            if r > 0:
                t.append("\n")
            if r == 1:
                t.append("  ")
            if r == 2:
                t.append("     ")
            for ch in row:
                ema = self.emas.get(ch)
                if ch == self.next_key:
                    t.append(f" {ch.upper()} ", style="bold black on #58a6ff")
                elif ema is None:
                    t.append(f" {ch} ", style="dim #6e7681 on #161b22")
                else:
                    t.append(f" {ch} ", style=f"bold {heat_color(ema)} on #161b22")
                t.append(" ")
        t.append("\n")
        t.append("  green = fast   amber = ok   red = slow   blue = next key", style="dim #8b949e")
        return t
