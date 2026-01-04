import os
import asyncio
from datetime import datetime, timedelta
from collections import Counter
from urllib.parse import urlparse

import discord
from discord.ext import commands

# ---------------- CONFIG ----------------
KNOWN_CLASSES = {
    "beer": "beer", "lager": "beer", "ipa": "beer",
    "wine": "wine", "red": "wine", "white": "wine",
    "shot": "shot", "vodka": "shot", "whiskey": "shot",
    "gin": "shot", "rum": "shot",
    "cocktail": "cocktail", "negroni": "cocktail", "martini": "cocktail",
}

USE_POSTGRES = "DATABASE_URL" in os.environ

if USE_POSTGRES:
    import psycopg

    def db():
        url = urlparse(os.environ["DATABASE_URL"])
        return psycopg.connect(
            host=url.hostname,
            port=url.port,
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            sslmode="require",
        )
else:
    import sqlite3
    DB_FILE = "beerbot.sqlite"

    def db():
        return sqlite3.connect(DB_FILE)

# ---------------- DB INIT ----------------
def init_db():
    if USE_POSTGRES:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS drink_logs (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    drink_name TEXT NOT NULL,
                    drink_class TEXT,
                    caption TEXT,
                    image_url TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_user_time ON drink_logs(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_time ON drink_logs(created_at);
                """)
    else:
        with db() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS drink_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                drink_name TEXT NOT NULL,
                drink_class TEXT,
                caption TEXT,
                image_url TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
            cur.close()
    print("✅ Database initialized")

# ---------------- UTILS ----------------
def classify(drink: str):
    return KNOWN_CLASSES.get(drink.lower())

def start_of_week():
    now = datetime.utcnow()
    return now - timedelta(days=now.weekday())

# ---------------- DISCORD ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# ---------------- COMMANDS ----------------
@bot.command()
async def ping(ctx):
    """Sanity check command"""
    await ctx.send("🏓 Pong!")

@bot.command()
async def drink(ctx, drink_name: str = "beer", *, caption: str = ""):
    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    drink_class = classify(drink_name)

    if USE_POSTGRES:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO drink_logs (user_id, username, drink_name, drink_class, caption, image_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (str(ctx.author.id), ctx.author.display_name, drink_name.lower(), drink_class, caption, image_url)
                )
    else:
        with db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO drink_logs (user_id, username, drink_name, drink_class, caption, image_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(ctx.author.id), ctx.author.display_name, drink_name.lower(), drink_class, caption, image_url)
            )
            conn.commit()
            cur.close()

    await ctx.send(f"🍻 Logged **{drink_name}** for {ctx.author.mention}")

@bot.command()
async def bulk(ctx, count: int, drink_name: str, *, caption: str = ""):
    drink_class = classify(drink_name)
    if USE_POSTGRES:
        with db() as conn:
            with conn.cursor() as cur:
                for _ in range(count):
                    cur.execute(
                        """
                        INSERT INTO drink_logs (user_id, username, drink_name, drink_class, caption)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (str(ctx.author.id), ctx.author.display_name, drink_name.lower(), drink_class, caption)
                    )
    else:
        with db() as conn:
            cur = conn.cursor()
            for _ in range(count):
                cur.execute(
                    """
                    INSERT INTO drink_logs (user_id, username, drink_name, drink_class, caption)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(ctx.author.id), ctx.author.display_name, drink_name.lower(), drink_class, caption)
                )
            conn.commit()
            cur.close()

    await ctx.send(f"🍺 Logged **{count}× {drink_name}** for {ctx.author.mention}")

@bot.command()
async def stats(ctx):
    with db() as conn:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("SELECT COUNT(*) FROM drink_logs WHERE user_id=%s", (str(ctx.author.id),))
            total = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) / GREATEST(EXTRACT(WEEK FROM AGE(MAX(created_at), MIN(created_at))),1)
                FROM drink_logs WHERE user_id=%s
            """, (str(ctx.author.id),))
            avg = cur.fetchone()[0]

            cur.execute("""
                SELECT drink_name, COUNT(*) FROM drink_logs
                WHERE user_id=%s
                GROUP BY drink_name ORDER BY COUNT(*) DESC LIMIT 1
            """, (str(ctx.author.id),))
            fav = cur.fetchone()

            cur.execute("SELECT MAX(created_at) FROM drink_logs WHERE user_id=%s", (str(ctx.author.id),))
            last = cur.fetchone()[0]
        else:
            cur.execute("SELECT COUNT(*) FROM drink_logs WHERE user_id=?", (str(ctx.author.id),))
            total = cur.fetchone()[0]

            cur.execute("SELECT MIN(created_at), MAX(created_at) FROM drink_logs WHERE user_id=?", (str(ctx.author.id),))
            min_max = cur.fetchone()
            weeks = max((datetime.utcnow() - datetime.fromisoformat(min_max[0])).days // 7, 1) if min_max[0] else 1
            avg = total / weeks

            cur.execute("SELECT drink_name, COUNT(*) FROM drink_logs WHERE user_id=? GROUP BY drink_name ORDER BY COUNT(*) DESC LIMIT 1", (str(ctx.author.id),))
            fav = cur.fetchone()

            cur.execute("SELECT MAX(created_at) FROM drink_logs WHERE user_id=?", (str(ctx.author.id),))
            last_row = cur.fetchone()
            last = last_row[0] if last_row else None

        if not USE_POSTGRES:
            cur.close()

    await ctx.send(
        f"📊 **{ctx.author.display_name}**\n"
        f"• Total: {total}\n"
        f"• Avg / week: {avg:.2f}\n"
        f"• Favourite: {fav[0] if fav else 'N/A'}\n"
        f"• Last drink: {last}"
    )

@bot.command()
async def leaderboard(ctx):
    since = start_of_week()
    with db() as conn:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("SELECT username, COUNT(*) FROM drink_logs WHERE created_at >= %s GROUP BY username ORDER BY COUNT(*) DESC LIMIT 10", (since,))
        else:
            cur.execute("SELECT username, COUNT(*) FROM drink_logs WHERE created_at >= ? GROUP BY username ORDER BY COUNT(*) DESC LIMIT 10", (since,))
        rows = cur.fetchall()
        if not USE_POSTGRES:
            cur.close()

    msg = "**🏆 Weekly Leaderboard**\n"
    for i, (u, c) in enumerate(rows, 1):
        msg += f"{i}. {u} — {c}\n"
    await ctx.send(msg)

# ---------------- MAIN ----------------
async def main():
    init_db()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("⚠️ DISCORD_TOKEN not set, bot cannot start.")
        return
    print("🚀 Starting bot...")
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
