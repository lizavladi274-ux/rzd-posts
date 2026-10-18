# -*- coding: utf-8 -*-
"""
Полный сбор постов карьерных каналов в базу career_posts.db.
  python parser.py            — Telegram и ВКонтакте
  python parser.py telegram   — только Telegram (ключ не нужен)
  python parser.py vk         — только ВКонтакте
Ключ ВКонтакте программа спросит при запуске; в коде и на GitHub он не хранится.
"""
import getpass, os, sys
from datetime import datetime, timezone
import config, storage, sources


def get_vk_token():
    return os.environ.get("VK_TOKEN") or getpass.getpass("Вставьте сервисный ключ ВКонтакте и нажмите Enter: ").strip()


def run(since, which=("telegram", "vk")):
    conn = storage.connect(config.DB_FILE)
    print(f"База данных: {config.DB_FILE}, собираем посты с {since:%Y-%m-%d}")
    if "telegram" in which:
        print("\n=== Telegram ===")
        for ch, company in config.TELEGRAM.items():
            try:
                rows = sources.collect_telegram(ch, company, since)
            except Exception as e:
                print(f"   ! {company}: не получилось ({e})"); continue
            print(f"   {company}: новых постов {storage.save(conn, rows)}, обновлено {len(rows)}")
    if "vk" in which:
        print("\n=== ВКонтакте ===")
        token = get_vk_token()
        for dom, company in config.VK.items():
            rows = sources.collect_vk(dom, company, token, since)
            print(f"   {company}: новых постов {storage.save(conn, rows)}, обновлено {len(rows)}")
    total = conn.execute("SELECT platform, company, COUNT(*) FROM posts GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    print("\nВ базе сейчас:")
    for p, c, n in total:
        print(f"   {p:9} {c:15} {n}")
    conn.close()


if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in ("telegram", "vk")] or ["telegram", "vk"]
    since = datetime.strptime(config.DATE_FROM, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    run(since, which)
