"""One-line roast for the Snooze Button Roast bounty.

The program emits a single roast of an alarm clock that rings at 6 AM on
a Saturday, writing it to ``$MAKEFUN_OUTPUT_DIR/entry.txt`` (falling back
to ``/output/entry.txt``). Nothing is written until the line has passed
every gate check, and the file itself is published in one atomic rename
so no reader can ever catch a partial entry.
"""

import os
import sys

# The winning line. The rooster image does the work twice: it names the
# alarm's job (crow at dawn) and then upgrades it to a professional with
# a LinkedIn profile — proud, ambitious, and completely unbothered that
# it is Saturday. The payoff belongs to the sun, which has not clocked
# in yet, so the alarm is officially keener than daylight. The em dash
# is the hinge: setup before it, punchline after it.
ROAST_LINE = (
    "The alarm went off at 6 AM on Saturday, proud as a rooster with "
    "a LinkedIn profile \u2014 even the sun hadn't clocked in yet."
)

LOWER_BOUND = 1
UPPER_BOUND = 200

# Standalone code points that are banned outright, whatever surrounds them.
BANNED_POINTS = ("\ufeff", "\u2028", "\u2029")

# Lone format characters that hide inside otherwise normal-looking text.
SNEAKY_FORMAT_POINTS = frozenset((0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD))


def _is_c1_control(value):
    """C1 control range U+0080..U+009F."""
    return 0x0080 <= value <= 0x009F


def _is_c0_control(value):
    """C0 controls below U+0020 (tab is already excluded by the line check)."""
    return value < 0x20


def _is_surrogate(value):
    """UTF-16 surrogate halves, which can never appear in valid UTF-8 text."""
    return 0xD800 <= value <= 0xDFFF


def _codepoint_is_hidden(value):
    """True when a code point is invisible junk rather than real content."""
    if _is_c1_control(value):
        return True
    if _is_c0_control(value):
        return True
    if value == 0x7F:
        return True
    if _is_surrogate(value):
        return True
    if value in SNEAKY_FORMAT_POINTS:
        return True
    return False


def _check_shape(line):
    """Reject empty, whitespace-only, over-long, or multi-line text."""
    if not isinstance(line, str):
        raise ValueError("entry must be a string")
    if not line or not line.strip():
        raise ValueError("entry must not be empty or whitespace-only")
    if len(line) < LOWER_BOUND or len(line) > UPPER_BOUND:
        raise ValueError(
            "entry must be %d-%d characters, got %d"
            % (LOWER_BOUND, UPPER_BOUND, len(line))
        )
    if "\n" in line or "\r" in line:
        raise ValueError("entry must be a single line")


def _check_characters(line):
    """Reject BOM / separators / invisible characters anywhere in the line."""
    for point in BANNED_POINTS:
        if point in line:
            raise ValueError(
                "entry contains forbidden character U+%04X" % ord(point)
            )
    for glyph in line:
        if _codepoint_is_hidden(ord(glyph)):
            raise ValueError(
                "entry contains invisible character U+%04X" % ord(glyph)
            )


def check_entry(line):
    """Raise ValueError unless *line* is a single valid gate-passing line."""
    _check_shape(line)
    _check_characters(line)
    return line


def _sweep_directory(path):
    """Delete every stale entry inside *path*; the directory itself stays."""
    for name in os.listdir(path):
        target = os.path.join(path, name)
        if os.path.isdir(target) and not os.path.islink(target):
            for inner in os.listdir(target):
                os.unlink(os.path.join(target, inner))
            os.rmdir(target)
        else:
            os.unlink(target)


def emit_entry(line, out_dir):
    """Atomically write *line* as entry.txt inside *out_dir*."""
    check_entry(line)
    os.makedirs(out_dir, exist_ok=True)
    _sweep_directory(out_dir)
    destination = os.path.join(out_dir, "entry.txt")
    # The staging file lives next to its destination on purpose: a rename
    # across filesystems would raise EXDEV, and /tmp is a different
    # filesystem from a bind-mounted output directory.
    staging = os.path.join(out_dir, ".entry.txt.tmp")
    payload = line.encode("utf-8")
    with open(staging, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(staging, 0o644)
    os.replace(staging, destination)
    os.chmod(destination, 0o644)
    # Confirm what landed on disk is exactly what we intended to write.
    with open(destination, "rb") as stream:
        if stream.read() != payload:
            raise ValueError("read-back verification failed")
    return destination


def run():
    """Entry point: resolve the output directory and publish the roast."""
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    target = emit_entry(ROAST_LINE, out_dir)
    print("wrote %s (%d chars)" % (target, len(ROAST_LINE)))
    return 0


if __name__ == "__main__":
    sys.exit(run())
