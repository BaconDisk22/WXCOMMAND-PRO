"""Conservative priority classifier for queued emergency broadcasts.

Only known urgent warning phrases are promoted. This never changes the
message content, destination, or radio channel.
"""
import re

URGENT_EVENTS = (
    "tornado warning",
    "flash flood warning",
    "tsunami warning",
    "extreme wind warning",
    "hurricane warning",
    "storm surge warning",
)


def is_urgent_weather(text: str) -> bool:
    """Return True for recognized life-threatening warning names.

    Word boundaries avoid accidentally promoting 'notatornado warning'.
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    return any(re.search(r"(?<!\w)" + re.escape(event) + r"(?!\w)", normalized)
               for event in URGENT_EVENTS)
