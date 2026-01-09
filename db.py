import psycopg2
import os
import logging

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = "beerbot_db"

def execute_query(query, params=None, fetch=False):
    try:
        with psycopg2.connect(
            host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=5432, sslmode="require"
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
    except Exception as e:
        logging.error(f"DB query failed: {e}")
        raise

def ensure_user_registered(discord_id, username, server_id, server_name):
    """Register user and server if missing, link user to server."""
    # User
    user_id = execute_query(
        "INSERT INTO users (discord_id, username) VALUES (%s, %s) "
        "ON CONFLICT (discord_id) DO UPDATE SET username=EXCLUDED.username RETURNING id;",
        (discord_id, username),
        fetch=True
    )[0][0]

    # Server
    execute_query(
        "INSERT INTO servers (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
        (server_id, server_name)
    )

    # Link user to server
    execute_query(
        "INSERT INTO server_members (user_id, server_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
        (user_id, server_id)
    )

    logging.info(f"Registered user {username} ({discord_id}) in server {server_name} ({server_id})")
    return user_id

def check_user_registered(discord_id):
    row = execute_query("SELECT id FROM users WHERE discord_id=%s;", (discord_id,), fetch=True)
    return row[0][0] if row else None

def log_drink(user_id, server_id, drink_name, quantity=1):
    execute_query(
        "INSERT INTO drinks (user_id, server_id, drink_name, quantity) VALUES (%s, %s, %s, %s);",
        (user_id, server_id, drink_name, quantity)
    )
    logging.info(f"Logged drink {quantity}x {drink_name} for user {user_id} in server {server_id}")
