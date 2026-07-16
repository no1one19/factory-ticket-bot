import pytest

import config
from config import parse_id_set


def test_parse_id_set() -> None:
    assert parse_id_set("1, 2,1") == frozenset({1, 2})
    assert parse_id_set("") == frozenset()


def test_parse_id_set_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="Invalid Telegram user ID"):
        parse_id_set("1,mechanic")


def test_ticket_viewer_ids_are_unique(monkeypatch) -> None:
    monkeypatch.setattr(config, "ADMIN_IDS", frozenset({1, 2}))
    monkeypatch.setattr(config, "MECHANIC_IDS", frozenset({2, 3}))

    assert config.ticket_viewer_ids() == frozenset({1, 2, 3})
