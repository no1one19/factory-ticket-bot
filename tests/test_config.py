import pytest

from config import parse_id_set


def test_parse_id_set() -> None:
    assert parse_id_set("1, 2,1") == frozenset({1, 2})
    assert parse_id_set("") == frozenset()


def test_parse_id_set_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Invalid Telegram user ID"):
        parse_id_set("1,mechanic")
