from typing import NamedTuple

import aiosqlite

from database.encryption import (
    decrypt_int,
    decrypt_value,
    encrypt_value,
    validate_encryption_key,
)

DB_NAME = "factory_bot.db"


class TicketCard(NamedTuple):
    id: int
    machine_number: str
    description: str
    photo_id: str
    criticality: str


class TicketReportRow(NamedTuple):
    id: int
    user_id: int
    machine_number: str
    description: str
    criticality: str
    status: str
    mechanic_id: int | None


def _ticket_card(row) -> TicketCard:
    ticket_id, machine_number, description, photo_id, criticality = row
    return TicketCard(
        ticket_id,
        decrypt_value(machine_number) or "",
        decrypt_value(description) or "",
        decrypt_value(photo_id) or "",
        decrypt_value(criticality) or "",
    )


async def _encrypt_legacy_rows(db: aiosqlite.Connection) -> bool:
    """Encrypt plaintext rows and validate rows encrypted with the current key."""
    async with db.execute(
        "SELECT id, user_id, machine_number, description, photo_id, "
        "criticality, mechanic_id FROM tickets"
    ) as cursor:
        rows = await cursor.fetchall()

    migrated = False
    for row in rows:
        (
            ticket_id,
            user_id,
            machine_number,
            description,
            photo_id,
            criticality,
            mechanic_id,
        ) = row
        encrypted = (
            encrypt_value(user_id),
            encrypt_value(machine_number),
            encrypt_value(description),
            encrypt_value(photo_id),
            encrypt_value(criticality),
            encrypt_value(mechanic_id),
        )
        original = tuple(
            str(value) if value is not None else None
            for value in (
                user_id,
                machine_number,
                description,
                photo_id,
                criticality,
                mechanic_id,
            )
        )
        if encrypted == original:
            continue

        await db.execute(
            """
            UPDATE tickets
            SET user_id = ?, machine_number = ?, description = ?, photo_id = ?,
                criticality = ?, mechanic_id = ?
            WHERE id = ?
            """,
            (*encrypted, ticket_id),
        )
        migrated = True

    return migrated


async def init_db() -> None:
    """Create the ticket table and encrypt any legacy plaintext rows."""
    validate_encryption_key()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("PRAGMA secure_delete = ON")
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                machine_number TEXT NOT NULL,
                description TEXT NOT NULL,
                photo_id TEXT NOT NULL,
                criticality TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                mechanic_id TEXT
            )
            """
        )
        migrated = await _encrypt_legacy_rows(db)
        await db.commit()
        if migrated:
            await db.execute("VACUUM")


async def create_ticket(
    user_id: int,
    machine_number: str,
    description: str,
    photo_id: str,
    criticality: str,
) -> int:
    """Create an encrypted ticket and return its database ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            INSERT INTO tickets
                (user_id, machine_number, description, photo_id, criticality)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                encrypt_value(user_id),
                encrypt_value(machine_number),
                encrypt_value(description),
                encrypt_value(photo_id),
                encrypt_value(criticality),
            ),
        )
        await db.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return the new ticket ID")
        return cursor.lastrowid


async def list_open_tickets() -> list[TicketCard]:
    """Return all tickets that can still be claimed."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, machine_number, description, photo_id, criticality "
            "FROM tickets WHERE status = 'open'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [_ticket_card(row) for row in rows]


async def get_open_ticket(ticket_id: int) -> TicketCard | None:
    """Return one open ticket, or None when it is no longer available."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, machine_number, description, photo_id, criticality "
            "FROM tickets WHERE id = ? AND status = 'open'",
            (ticket_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return _ticket_card(row) if row else None


async def list_tickets_for_report() -> list[TicketReportRow]:
    """Return decrypted ticket data for an authorized admin report."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, user_id, machine_number, description, criticality, "
            "status, mechanic_id FROM tickets"
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        TicketReportRow(
            ticket_id,
            decrypt_int(user_id),
            decrypt_value(machine_number) or "",
            decrypt_value(description) or "",
            decrypt_value(criticality) or "",
            status,
            decrypt_int(mechanic_id),
        )
        for (
            ticket_id,
            user_id,
            machine_number,
            description,
            criticality,
            status,
            mechanic_id,
        ) in rows
    ]


async def claim_ticket(ticket_id: int, mechanic_id: int) -> int | None:
    """Atomically claim an open ticket and return its owner's Telegram ID."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            UPDATE tickets
            SET status = 'in_progress', mechanic_id = ?
            WHERE id = ? AND status = 'open'
            """,
            (encrypt_value(mechanic_id), ticket_id),
        )
        await db.commit()
        if cursor.rowcount != 1:
            return None

        async with db.execute(
            "SELECT user_id FROM tickets WHERE id = ?", (ticket_id,)
        ) as result:
            row = await result.fetchone()
            return decrypt_int(row[0]) if row else None


async def finish_ticket(ticket_id: int, mechanic_id: int) -> int | None:
    """Close a ticket only when it belongs to the requesting mechanic."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute(
            "SELECT user_id, mechanic_id, status FROM tickets WHERE id = ?",
            (ticket_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if (
            row is None
            or row[2] != "in_progress"
            or decrypt_int(row[1]) != mechanic_id
        ):
            await db.rollback()
            return None

        cursor = await db.execute(
            """
            UPDATE tickets
            SET status = 'closed'
            WHERE id = ? AND status = 'in_progress'
            """,
            (ticket_id,),
        )
        if cursor.rowcount != 1:
            await db.rollback()
            return None
        await db.commit()
        return decrypt_int(row[0])
