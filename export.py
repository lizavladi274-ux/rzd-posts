# -*- coding: utf-8 -*-
"""
Выгружает базу в таблицу career_posts.csv и считает индексы по методике проекта:
  индекс охвата        = просмотры поста / медиана просмотров обычных постов канала за ±45 дней
  индекс вовлечённости = (реакции / просмотры) / медиана этой доли за те же ±45 дней
Обычные посты — без репостов чужих записей и рекламы; медиана считается, если в окне не меньше 30 постов.
  python export.py
"""
import sqlite3
import numpy as np, pandas as pd
import config

conn = sqlite3.connect(config.DB_FILE)
df = pd.read_sql_query("SELECT * FROM posts ORDER BY platform, company, date_utc", conn)
conn.close()

df["when"] = pd.to_datetime(df.date_utc)
df["share"] = np.where(df.views > 0, df.reactions / df.views, np.nan)
df["ordinary"] = (df.is_forward == 0) & (df.is_ad == 0) & (df.views > 0)
df["i_reach"] = np.nan
df["i_eng"] = np.nan
WIN, MIN_N = pd.Timedelta(days=45), 30

for (pl, ch), g in df.groupby(["platform", "channel"]):
    base = g[g.ordinary]
    for i, row in g.iterrows():
        w = base[(base.when >= row.when - WIN) & (base.when <= row.when + WIN) & (base.index != i)]
        if pl == "vk":                                  # во ВКонтакте видео сравниваем только с видео
            w = w[(w.media == "video") == (row.media == "video")]
        if len(w) < MIN_N or not row.views:
            continue
        df.loc[i, "i_reach"] = row.views / w.views.median()
        med = w.share.median()
        if med and med > 0:
            df.loc[i, "i_eng"] = row.share / med

df = df.drop(columns=["when", "share", "ordinary"])
df["i_reach"] = df.i_reach.round(3)
df["i_eng"] = df.i_eng.round(3)
df.to_csv("career_posts.csv", index=False, encoding="utf-8-sig")   # utf-8-sig — чтобы Excel открыл без «кракозябр»
print(f"Сохранено в career_posts.csv: {len(df)} постов, с индексами {df.i_reach.notna().sum()}")
print(df.groupby(["platform", "company"]).agg(постов=("post_id", "size"),
      медиана_просмотров=("views", "median"), с_индексом=("i_reach", "count")).to_string())
