from flask import Flask, render_template
import os
from datetime import datetime, timedelta
from collections import Counter

USE_POSTGRES = "DATABASE_URL" in os.environ

if USE_POSTGRES:
    import psycopg2
    from urllib.parse import urlparse

    def db():
        url = urlparse(os.environ["DATABASE_URL"])
        return psycopg2.connect(
            dbname=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port,
        )
else:
    import sqlite3
    DB_FILE = "beerbot.sqlite"

    def db():
        return sqlite3.connect(DB_FILE)

app = Flask(__name__)


@app.route("/")
def leaderboard():
    conn = db()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT username, COUNT(*) AS total
            FROM drink_logs
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY username
            ORDER BY total DESC
        """)
    else:
        week_ago = datetime.utcnow() - timedelta(days=7)
        cur.execute("""
            SELECT username, COUNT(*) AS total
            FROM drink_logs
            WHERE created_at >= ?
            GROUP BY username
            ORDER BY total DESC
        """, (week_ago,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("leaderboard.html", rows=rows)


@app.route("/me/<user_id>")
def me(user_id):
    conn = db()
    cur = conn.cursor()
    if USE_POSTGRES:
        # All drinks for user
        cur.execute("""
            SELECT drink_name, drink_class, caption, image_url, created_at
            FROM drink_logs
            WHERE user_id=%s
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
    else:
        cur.execute("""
            SELECT drink_name, drink_class, caption, image_url, created_at
            FROM drink_logs
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
    drinks = cur.fetchall()
    cur.close()
    conn.close()

    # Stats
    total = len(drinks)
    last_drinks = drinks[:5]
    per_class = Counter([d[1] for d in drinks if d[1]])
    favorite = per_class.most_common(1)[0][0] if per_class else None

    # Drinks per week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_count = sum(1 for d in drinks if d[4] >= one_week_ago)

    return render_template(
        "me.html",
        drinks=drinks,
        total=total,
        favorite=favorite,
        last_drinks=last_drinks,
        weekly_count=weekly_count,
    )


"""
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
"""