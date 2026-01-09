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

client = discord.Client(intents=intents)

print("Connecting to db...")

# Setup postgres python connection
conn = psycopg2.connect(
    host=DB_HOST,  
    dbname="beerbot_db",
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

@client.event
async def on_message(msg):
    if msg.author == client.user: return

    if msg.content.startswith("$hello"):
        await msg.channel.send("Hello from Beerbot!")

# Driver code
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    client.run(TOKEN)