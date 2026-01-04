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
"""

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
