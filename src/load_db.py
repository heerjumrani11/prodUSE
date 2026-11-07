from pathlib import Path

import psycopg

HOST = "localhost"
DB_NAME = "produse"

# Each table and the CSV file that fills it.
TABLES = [
    ("users", "data/users.csv"),
    ("events", "data/events.csv"),
    ("subscriptions", "data/subscriptions.csv"),
    ("feedback", "data/feedback.csv"),
]

# Part 1: create the produse database if it does not exist yet.
with psycopg.connect(host=HOST, dbname="postgres", autocommit=True) as conn:
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
    ).fetchone()
    if not exists:
        conn.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Created database {DB_NAME}")

# Part 2: build the tables and fill them from the CSV files.
with psycopg.connect(host=HOST, dbname=DB_NAME) as conn:
    conn.execute(Path("src/schema.sql").read_text())
    for table, csv_path in TABLES:
        with conn.cursor() as cur:
            # COPY is the fast way to load a whole file into a table.
            with cur.copy(
                f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)"
            ) as copy:
                with open(csv_path) as f:
                    while chunk := f.read(65536):
                        copy.write(chunk)
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")