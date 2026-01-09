import discord
import psycopg2
import os

import threading
from flask import Flask

# Set up discord connection
intents = discord.Intents.default()
intents.message_content=True

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN: TOKEN = TOKEN.strip()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = "beerbot_db"

client = discord.Client(intents=intents)

# DB functionality
def execute_query(query, params=None, fetch=False):
    """Atomic DB helper: open connection, execute query, optionally fetch results"""
    with psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=5432, sslmode="require"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()

def register_user(discord_id, username):
    query = """
    INSERT INTO users (discord_id, username)
    VALUES (%s, %s)
    ON CONFLICT (discord_id) DO NOTHING
    RETURNING id;
    """
    result = execute_query(query, (discord_id, username), fetch=True)
    return result[0][0] if result else None

def log_drink(discord_id, drink_name, quantity=1):
    # Get user id
    user = execute_query("SELECT id FROM users WHERE discord_id=%s;", (discord_id,), fetch=True)
    if not user:
        return False, "You must register first using $register"
    user_id = user[0][0]

    # Insert drink
    execute_query(
        "INSERT INTO drinks (user_id, drink_name, quantity) VALUES (%s, %s, %s);",
        (user_id, drink_name, quantity)
    )
    return True, f"Logged {quantity} x {drink_name} for your account"

def get_leaderboard():
    rows = execute_query(
        "SELECT username, drinks_this_week FROM weekly_leaderboard;", fetch=True
    )
    if not rows:
        return "No drinks logged this week."
    msg = "**Weekly Leaderboard:**\n"
    for i, (username, count) in enumerate(rows, start=1):
        msg += f"{i}. {username}: {count} drinks\n"
    return msg

def get_history(discord_id):
    user = execute_query("SELECT id FROM users WHERE discord_id=%s;", (discord_id,), fetch=True)
    if not user:
        return "You must register first using $register"
    user_id = user[0][0]

    rows = execute_query(
        "SELECT drink_name, quantity, created_at FROM drinks WHERE user_id=%s ORDER BY created_at DESC;",
        (user_id,), fetch=True
    )
    if not rows:
        return "You have no drink history."
    
    msg = "**Your Drink History:**\n"
    for drink_name, quantity, created_at in rows:
        msg += f"{created_at.date()}: {quantity} x {drink_name}\n"
    return msg

# End of DB helpers

print("Connecting to db...")

# Setup postgres python connection
conn = psycopg2.connect(
    host=DB_HOST,  
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    port=5432,
    sslmode="require"  # must have for Render
)
cur = conn.cursor()
cur.close()

print("Connected to db!")

# Setup web server
app = Flask(__name__)

@app.route("/")
def home():
    return "Beerbot is running!"

def run_web():
    port=int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Discord events
@client.event
async def on_ready():
    print(f"Beerbot logged in as {client.user}")

# Command handlers (for event handler)
async def handle_hello(msg):
    await msg.channel.send(f"👋 Hello {msg.author}! Beerbot is here to keep track of your drinks 🍻")

async def handle_register(msg):
    user_id = register_user(msg.author.id, str(msg.author))
    if user_id:
        await msg.channel.send(f"✅ Registered {msg.author}! Get ready to track your 🍺 adventures!")
    else:
        await msg.channel.send(f"⚠️ {msg.author}, you are already registered! Let's keep drinking 🍻")

async def handle_drink(msg):
    parts = msg.content.strip().split()
    if len(parts) < 2:
        await msg.channel.send("Usage: `$drink <drink_name> [quantity]` 🍹")
        return

    # Support multi-word drink names: all except last token if numeric
    if len(parts) > 2 and parts[-1].isdigit():
        quantity = int(parts[-1])
        drink_name = " ".join(parts[1:-1])
    else:
        quantity = 1
        drink_name = " ".join(parts[1:])

    success, response = log_drink(msg.author.id, drink_name, quantity)
    emoji = "🍺" if success else "⚠️"
    await msg.channel.send(f"{emoji} {response}")

async def handle_leaderboard(msg):
    leaderboard = get_leaderboard()
    leaderboard_msg = f"🏆 **Weekly Leaderboard** 🏆\n{leaderboard}"
    await msg.channel.send(leaderboard_msg)

async def handle_history(msg):
    history = get_history(msg.author.id)
    history_msg = f"📜 **Your Drink History** 📜\n{history}"
    await msg.channel.send(history_msg)

# Message event handler
@client.event
async def on_message(msg):
    if msg.author == client.user: return
    content = msg.content.strip().lower()
    if content.startswith("$hello"):
        await handle_hello(msg)
    elif content.startswith("$register"):
        await handle_register(msg)
    elif content.startswith("$drink"):
        await handle_drink(msg)
    elif content.startswith("$leaderboard"):
        await handle_leaderboard(msg)
    elif content.startswith("$history"):
        await handle_history(msg)


# Driver code
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    client.run(TOKEN)