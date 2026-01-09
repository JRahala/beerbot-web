import discord
import psycopg2
import os
import threading
from flask import Flask
import logging

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("beerbot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def log_action(action: str):
    logging.info(action)

# ---------------------------
# Config
# ---------------------------
intents = discord.Intents.default()
intents.message_content = True

TOKEN = os.getenv('DISCORD_TOKEN').strip()
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = "beerbot_db"

# ---------------------------
# Discord Client
# ---------------------------
class BeerBotClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

client = BeerBotClient()

# ---------------------------
# DB helpers
# ---------------------------
def execute_query(query, params=None, fetch=False):
    with psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=5432,
        sslmode="require"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()

def ensure_server(server_id, server_name):
    """Ensure server exists in DB."""
    execute_query(
        "INSERT INTO servers (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
        (server_id, server_name)
    )

def register_user(discord_id, username, server_id=None, server_name=None):
    """Register user and optionally server, return user_id"""
    if server_id:
        ensure_server(server_id, server_name)

    rows = execute_query(
        "INSERT INTO users (discord_id, username) VALUES (%s, %s) "
        "ON CONFLICT (discord_id) DO UPDATE SET username=EXCLUDED.username "
        "RETURNING id;",
        (discord_id, username),
        fetch=True
    )
    user_id = rows[0][0]

    if server_id:
        # link user to server
        execute_query(
            "INSERT INTO server_members (user_id, server_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (user_id, server_id)
        )

    log_action(f"Registered user {username} ({discord_id})")
    return user_id

def log_drink(discord_id, server_id, server_name, drink_name, quantity=1):
    # Ensure server exists
    ensure_server(server_id, server_name)

    # Check user
    user = execute_query(
        "SELECT id FROM users WHERE discord_id=%s;", 
        (discord_id,), fetch=True
    )
    if not user:
        # Auto-register user for this server
        user_id = register_user(discord_id, f"User#{discord_id}", server_id, server_name)
    else:
        user_id = user[0][0]

    # Log drink
    execute_query(
        "INSERT INTO drinks (user_id, server_id, drink_name, quantity) VALUES (%s, %s, %s, %s);",
        (user_id, server_id, drink_name, quantity)
    )
    return True, f"Logged {quantity} x {drink_name} 🍺"


# ---------------------------
# Web server
# ---------------------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Beerbot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------------------
# Commands
# ---------------------------
@client.tree.command(name="register", description="Register your account ✅")
async def register_command(interaction: discord.Interaction):
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(thinking=True)

        # Ensure server exists
        execute_query(
            "INSERT INTO servers (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (interaction.guild.id, interaction.guild.name)
        )

        # Ensure user exists and link to server
        user_id = execute_query(
            "INSERT INTO users (discord_id, username) VALUES (%s, %s) "
            "ON CONFLICT (discord_id) DO UPDATE SET username=EXCLUDED.username RETURNING id;",
            (interaction.user.id, str(interaction.user)), fetch=True
        )[0][0]

        execute_query(
            "INSERT INTO server_members (user_id, server_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (user_id, interaction.guild.id)
        )

        # Send followup after all DB ops
        await interaction.followup.send(f"✅ {interaction.user} registered in {interaction.guild.name}!")

        logging.info(f"Registered user {interaction.user} ({interaction.user.id}) in server {interaction.guild.name} ({interaction.guild.id})")

    except Exception as e:
        logging.error(f"Error in register_command: {e}")
        try:
            await interaction.followup.send(f"⚠️ Registration failed: {e}")
        except Exception as e2:
            logging.error(f"Failed to send followup: {e2}")

@client.tree.command(name="drink", description="Log a drink 🍺")
@discord.app_commands.describe(drink_name="Name of the drink", quantity="Quantity (default 1)")
async def drink_command(interaction: discord.Interaction, drink_name: str, quantity: int = 1):
    try:
        # Defer immediately to prevent 404
        await interaction.response.defer(thinking=True)

        # Check if user exists
        user_row = execute_query(
            "SELECT id FROM users WHERE discord_id=%s;", 
            (interaction.user.id,), fetch=True
        )
        if not user_row:
            # User not registered
            await interaction.followup.send(
                f"⚠️ You are not registered yet! Please use `/register` first before logging drinks."
            )
            return

        user_id = user_row[0][0]

        # Ensure server exists
        execute_query(
            "INSERT INTO servers (id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (interaction.guild.id, interaction.guild.name)
        )

        # Link user to server if missing
        execute_query(
            "INSERT INTO server_members (user_id, server_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
            (user_id, interaction.guild.id)
        )

        # Log the drink
        execute_query(
            "INSERT INTO drinks (user_id, server_id, drink_name, quantity) VALUES (%s, %s, %s, %s);",
            (user_id, interaction.guild.id, drink_name, quantity)
        )

        await interaction.followup.send(f"🍺 Logged {quantity} x {drink_name} for {interaction.user}!")

        logging.info(f"Logged drink {quantity}x {drink_name} for {interaction.user} ({user_id}) in server {interaction.guild.id}")

    except Exception as e:
        logging.error(f"Error in drink_command: {e}")
        try:
            await interaction.followup.send(f"⚠️ Could not log drink due to an error: {e}")
        except Exception as e2:
            logging.error(f"Failed to send followup: {e2}")

# ---------------------------
# on_ready
# ---------------------------
@client.event
async def on_ready():
    await client.tree.sync()
    print(f"Beerbot logged in as {client.user}")

# ---------------------------
# Driver
# ---------------------------
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    client.run(TOKEN)
