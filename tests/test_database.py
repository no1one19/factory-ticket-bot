import aiosqlite
import pytest

from database import database


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_NAME", str(path))
    return path


async def _create_ticket(db_path) -> int:
    await database.init_db()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO tickets
                (user_id, machine_number, description, photo_id, criticality)
            VALUES (?, ?, ?, ?, ?)
            """,
            (100, "M-1", "broken", "photo", "critical"),
        )
        await db.commit()
        return cursor.lastrowid


@pytest.mark.asyncio
async def test_ticket_can_only_be_claimed_once(db_path) -> None:
    ticket_id = await _create_ticket(db_path)

    assert await database.claim_ticket(ticket_id, 200) == 100
    assert await database.claim_ticket(ticket_id, 201) is None


@pytest.mark.asyncio
async def test_only_assigned_mechanic_can_finish_ticket(db_path) -> None:
    ticket_id = await _create_ticket(db_path)
    await database.claim_ticket(ticket_id, 200)

    assert await database.finish_ticket(ticket_id, 201) is None
    assert await database.finish_ticket(ticket_id, 200) == 100
    assert await database.finish_ticket(ticket_id, 200) is None
