import discord
import os
import threading
from flask import Flask
import logging
from commands import register_command, drink_command, hello_command
from discord import app_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("beerbot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

TOKEN = os.getenv('DISCORD_TOKEN').strip()
intents = discord.Intents.default()
intents.message_content = True

# Discord Client
class BeerBotClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

client = BeerBotClient()

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
# Register commands
# ---------------------------
# Register commands
client.tree.add_command(app_commands.Command(
    name="hello",
    description="Say hello",
    callback=hello_command
))

client.tree.add_command(app_commands.Command(
    name="register",
    description="Register account",
    callback=register_command
))

client.tree.add_command(app_commands.Command(
    name="drink",
    description="Log a drink",
    callback=drink_command
))


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
