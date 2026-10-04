# wpm and accuracy math, kept separate so its easy to test
def calc_wpm(correct_chars, elapsed_seconds):
    # standard formula: groups of 5 chars = 1 word, divided by minutes
    if elapsed_seconds <= 0 or correct_chars <= 0:
        return 0.0
    minutes = elapsed_seconds / 60.0
    return (correct_chars / 5.0) / minutes

# accuracy as a 0-100 percent number
def calc_accuracy(correct_keystrokes, total_keystrokes):
    if total_keystrokes <= 0:
        return 100.0
    return (correct_keystrokes / total_keystrokes) * 100.0

# live wpm for while youre typing, hides the jumpy first second
def calc_live_wpm(correct_chars, elapsed_seconds):
    if elapsed_seconds < 1.0:
        return 0.0
    return calc_wpm(correct_chars, elapsed_seconds)
