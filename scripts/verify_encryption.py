import argparse
import asyncio
import sqlite3

from dotenv import load_dotenv

from database import database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", help="Path to the SQLite database to verify")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()
    database.DB_NAME = args.database
    asyncio.run(database.init_db())

    connection = sqlite3.connect(args.database)
    try:
        total = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        encrypted = connection.execute(
            """
            SELECT COUNT(*) FROM tickets
            WHERE CAST(user_id AS TEXT) LIKE 'enc:v1:%'
              AND machine_number LIKE 'enc:v1:%'
              AND description LIKE 'enc:v1:%'
              AND photo_id LIKE 'enc:v1:%'
              AND criticality LIKE 'enc:v1:%'
              AND (mechanic_id IS NULL OR mechanic_id LIKE 'enc:v1:%')
            """
        ).fetchone()[0]
    finally:
        connection.close()

    print(f"Total rows: {total}")
    print(f"Fully encrypted rows: {encrypted}")
    if total != encrypted:
        raise SystemExit("Encryption verification failed")


if __name__ == "__main__":
    main()
