from app.bot.payload import Action, decode, encode


def test_encode_simple():
    assert encode("h") == "h"


def test_encode_with_args():
    assert encode("pd", 12, 0) == "pd:12:0"


def test_decode_simple():
    assert decode("h") == Action(screen="h", args=[])


def test_decode_with_args():
    assert decode("apply:12:3") == Action(screen="apply", args=["12", "3"])


def test_roundtrip():
    payload = encode("pd", 42, 1)
    action = decode(payload)
    assert action.screen == "pd"
    assert [int(a) for a in action.args] == [42, 1]
