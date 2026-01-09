import os
import psycopg2

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = "beerbot_db"

if not (DB_USER and DB_PASSWORD and DB_HOST):
    raise EnvironmentError("Make sure DB_USER, DB_PASSWORD, and DB_HOST are set")

# Create table and leaderboard view
INIT_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Drinks table
CREATE TABLE IF NOT EXISTS drinks (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    drink_name TEXT NOT NULL,
    quantity INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Weekly leaderboard view
CREATE OR REPLACE VIEW weekly_leaderboard AS
SELECT u.username,
       COUNT(d.id) AS drinks_this_week
FROM users u
LEFT JOIN drinks d
  ON u.id = d.user_id
 AND d.created_at >= date_trunc('week', NOW())
GROUP BY u.username
ORDER BY drinks_this_week DESC;
"""


def init_db():
    print("Connecting to database...")
    try:
        with psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=5432,
            sslmode="require"
        ) as conn:
            print("Connected to db!")
            with conn.cursor() as cur:
                cur.execute(INIT_SQL)
                conn.commit()
                print("Database initialized successfully!")

    except Exception as e:
        print("Error initializing database:", e)

if __name__ == "__main__":
    init_db()
