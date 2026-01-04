"""
import threading
import os
from bot import run_bot
from web import app

# Start Discord bot in background
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

import asyncio
import os
from bot import bot, init_db
from web import app

async def start_bot():
    init_db()
    token = os.environ["DISCORD_TOKEN"]
    print("Bot is starting...")
    await bot.start(token)

# Start bot in background
loop = asyncio.get_event_loop()
loop.create_task(start_bot())

# Run Flask using a production server
from waitress import serve  # install waitress via pip
port = int(os.environ.get("PORT", 8080))
serve(app, host="0.0.0.0", port=port)
"""

import os
import asyncio
from bot import bot, init_db
from web import app
from threading import Thread

# ---------------- BOT RUNNER ----------------
def run_bot():
    """Runs the Discord bot in the event loop."""
    init_db()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("⚠️ DISCORD_TOKEN not set, bot cannot start.")
        return
    print("🚀 Starting bot...")
    asyncio.run(bot.start(token))

# Run bot in a separate thread
bot_thread = Thread(target=run_bot, daemon=True)
bot_thread.start()

# ---------------- FLASK RUNNER ----------------
# Use Waitress for production (Render)
from waitress import serve

port = int(os.environ.get("PORT", 8080))
print(f"🌐 Starting Flask on port {port}...")
serve(app, host="0.0.0.0", port=port)
