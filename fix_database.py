import sqlite3
from pathlib import Path

# Use the database located beside this script
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "devices.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Check whether the devices table exists
    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'devices'
    """)

    if cursor.fetchone() is None:
        print("The devices table does not exist.")
        print("Please check your database setup.")
    else:
        # Read the existing columns
        cursor.execute("PRAGMA table_info(devices)")
        columns = {
            row[1] for row in cursor.fetchall()
        }

        # Add the missing owner column
        if "owner" not in columns:
            cursor.execute(
                "ALTER TABLE devices ADD COLUMN owner TEXT"
            )
            print("Added missing column: owner")
        else:
            print("Column owner already exists.")

        # Add the missing created_at column
        if "created_at" not in columns:
            cursor.execute(
                "ALTER TABLE devices ADD COLUMN created_at TEXT"
            )
            print("Added missing column: created_at")
        else:
            print("Column created_at already exists.")

        # Fill missing creation timestamps
        cursor.execute("""
            UPDATE devices
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL
        """)

        conn.commit()
        print("\nDatabase update completed successfully!")

except sqlite3.Error as error:
    conn.rollback()
    print("Database update failed:", error)

finally:
    conn.close()
