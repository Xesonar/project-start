"""Compact, colon-delimited payload strings carried on inline_keyboard
callback buttons — MAX round-trips whatever we put in `payload` back to us
unchanged on message_callback, so this is the only state we get for free."""

from dataclasses import dataclass, field


@dataclass
class Action:
    screen: str
    args: list[str] = field(default_factory=list)


def encode(screen: str, *args: object) -> str:
    parts = [screen, *(str(a) for a in args)]
    return ":".join(parts)


def decode(payload: str) -> Action:
    parts = payload.split(":")
    return Action(screen=parts[0], args=parts[1:])
