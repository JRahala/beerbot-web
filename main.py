import threading
from bot import run_bot   # your bot.py exposes a run_bot() function
from web import app       # your web.py exposes Flask app

# Start Discord bot in a separate thread
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

# Start Flask web server on Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
