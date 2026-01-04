import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import psycopg2
from urllib.parse import urlparse

# ---------------- CONFIG ----------------
KNOWN_CLASSES = {
    "beer": "beer",
    "lager": "beer",
    "ipa": "beer",
    "wine": "wine",
    "red": "wine",
    "white": "wine",
    "shot": "shot",
    "vodka": "shot",
    "whiskey": "shot",
    "gin": "shot",
    "rum": "shot",
    "cocktail": "cocktail",
    "negroni": "cocktail",
    "martini": "cocktail",
}

# ---------------- DB ----------------
def db():
    url = urlparse(os.environ["DATABASE_URL"])
    return psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
    )

def init_db():
    """Create the drink_logs table if it doesn't exist"""
    conn = db()
    cur = conn.cursor()
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
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized")

def classify(drink: str):
    d = drink.lower()
    return KNOWN_CLASSES.get(d)

def start_of_week():
    now = datetime.utcnow()
    return now - timedelta(days=now.weekday())

# ---------------- DISCORD ----------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
init_db()

# ---------------- EVENTS ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- COMMANDS ----------------
@bot.command()
async def drink(ctx, drink_name: str = "beer", *, caption: str = ""):
    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    drink_class = classify(drink_name)

    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO drink_logs
        (user_id, username, drink_name, drink_class, caption, image_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            str(ctx.author.id),
            ctx.author.display_name,
            drink_name.lower(),
            drink_class,
            caption,
            image_url,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

    await ctx.send(f"🍻 Logged **{drink_name}** for {ctx.author.mention}")

@bot.command()
async def bulk(ctx, count: int, drink_name: str, *, caption: str = ""):
    drink_class = classify(drink_name)

    conn = db()
    cur = conn.cursor()
    for _ in range(count):
        cur.execute(
            """
            INSERT INTO drink_logs
            (user_id, username, drink_name, drink_class, caption)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                str(ctx.author.id),
                ctx.author.display_name,
                drink_name.lower(),
                drink_class,
                caption,
            ),
        )
    conn.commit()
    cur.close()
    conn.close()

    await ctx.send(f"🍺 Logged **{count}× {drink_name}** for {ctx.author.mention}")

@bot.command()
async def stats(ctx):
    conn = db()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM drink_logs WHERE user_id=%s",
        (str(ctx.author.id),),
    )
    total = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*) / GREATEST(EXTRACT(WEEK FROM AGE(MAX(created_at), MIN(created_at))),1)
        FROM drink_logs WHERE user_id=%s
        """,
        (str(ctx.author.id),),
    )
    avg = cur.fetchone()[0]

    cur.execute(
        """
        SELECT drink_name, COUNT(*) FROM drink_logs
        WHERE user_id=%s
        GROUP BY drink_name ORDER BY COUNT(*) DESC LIMIT 1
        """,
        (str(ctx.author.id),),
    )
    fav = cur.fetchone()

    cur.execute(
        """
        SELECT MAX(created_at) FROM drink_logs WHERE user_id=%s
        """,
        (str(ctx.author.id),),
    )
    last = cur.fetchone()[0]

    cur.close()
    conn.close()

    await ctx.send(
        f"📊 **{ctx.author.display_name}**\n"
        f"• Total: {total}\n"
        f"• Avg / week: {avg:.2f}\n"
        f"• Favourite: {fav[0] if fav else 'N/A'}\n"
        f"• Last drink: {last}"
    )

@bot.command()
async def leaderboard(ctx):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, COUNT(*) FROM drink_logs
        WHERE created_at >= %s
        GROUP BY username ORDER BY COUNT(*) DESC LIMIT 10
        """,
        (start_of_week(),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    msg = "**🏆 Weekly Leaderboard**\n"
    for i, (u, c) in enumerate(rows, 1):
        msg += f"{i}. {u} — {c}\n"
    await ctx.send(msg)

# ---------------- RUN ----------------
def run_bot():
    token=os.environ["DISCORD_TOKEN"]
    bot.run(token)
