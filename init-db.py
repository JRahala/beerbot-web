import os
import psycopg2

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = "beerbot_db"

if not (DB_USER and DB_PASSWORD and DB_HOST):
    raise EnvironmentError("Make sure DB_USER, DB_PASSWORD, and DB_HOST are set")

INIT_SQL = """
-- Users table (same account across servers)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Servers table
CREATE TABLE servers (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL
);

-- User-Server association
CREATE TABLE server_members (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    server_id BIGINT REFERENCES servers(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, server_id)
);

-- Drinks table
CREATE TABLE drinks (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    server_id BIGINT REFERENCES servers(id) ON DELETE CASCADE,
    drink_name TEXT NOT NULL,
    quantity INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Leaderboard view per server
CREATE OR REPLACE VIEW weekly_leaderboard AS
SELECT s.id AS server_id, u.username, SUM(d.quantity) AS drinks_this_week
FROM drinks d
JOIN users u ON d.user_id = u.id
JOIN servers s ON d.server_id = s.id
WHERE d.created_at >= date_trunc('week', NOW())
GROUP BY s.id, u.username
ORDER BY s.id, drinks_this_week DESC;

"""

def init_db():
    try:
        print("Connecting to default database to recreate beerbot_db...")
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        )

        # **Important:** enable autocommit before executing DROP/CREATE
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME};")
            print(f"Dropped database {DB_NAME} if it existed.")

            cur.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"Created new database {DB_NAME}.")

        conn.close()

        # Connect to the new database to initialize tables
        print(f"Connecting to new database {DB_NAME} to create tables...")
        with psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(INIT_SQL)
                conn.commit()
                print("Tables and views created successfully!")

    except Exception as e:
        print("Error initializing database:", e)

if __name__ == "__main__":
    init_db()
