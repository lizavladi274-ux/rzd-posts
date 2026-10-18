# -*- coding: utf-8 -*-
"""База данных SQLite: одна таблица posts, одна строка = один пост."""
import sqlite3

COLUMNS = ["platform", "channel", "company", "post_id", "url", "date_utc", "text", "media",
           "views", "reactions", "likes", "reposts", "comments",
           "is_forward", "is_ad", "is_pinned", "subscribers", "updated_utc"]
COUNTERS = ["views", "reactions", "likes", "reposts", "comments", "subscribers", "updated_utc"]


def connect(db_file):
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            platform TEXT, channel TEXT, company TEXT, post_id INTEGER, url TEXT,
            date_utc TEXT, text TEXT, media TEXT,
            views INTEGER, reactions INTEGER, likes INTEGER, reposts INTEGER, comments INTEGER,
            is_forward INTEGER, is_ad INTEGER, is_pinned INTEGER, subscribers INTEGER, updated_utc TEXT,
            PRIMARY KEY (platform, channel, post_id)
        )""")
    return conn


def save(conn, rows):
    """Новые посты добавляет, у уже известных обновляет только счётчики."""
    if not rows:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    sql = (f"INSERT INTO posts ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))}) "
           f"ON CONFLICT(platform, channel, post_id) DO UPDATE SET "
           + ", ".join(f"{c} = excluded.{c}" for c in COUNTERS))
    conn.executemany(sql, [[r.get(c) for c in COLUMNS] for r in rows])
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] - before
