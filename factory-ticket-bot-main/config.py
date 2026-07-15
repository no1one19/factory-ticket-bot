import os


def parse_id_set(value: str | None) -> frozenset[int]:
    if not value:
        return frozenset()

    ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError as exc:
            raise ValueError(f"Invalid Telegram user ID: {item!r}") from exc
    return frozenset(ids)


ADMIN_IDS = parse_id_set(os.getenv("ADMIN_IDS"))
MECHANIC_IDS = parse_id_set(os.getenv("MECHANIC_IDS"))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_mechanic(user_id: int) -> bool:
    return user_id in MECHANIC_IDS or is_admin(user_id)
