# -*- coding: utf-8 -*-
"""
Обновляет просмотры, реакции и лайки у постов за последние N дней
(у свежих постов счётчики ещё растут). Новые посты за это время тоже добавятся.
  python update_stats.py        — последние 30 дней
  python update_stats.py 60     — последние 60 дней
"""
import sys
from datetime import datetime, timedelta, timezone
import parser

days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
which = [a for a in sys.argv[1:] if a in ("telegram", "vk")] or ["telegram", "vk"]
print(f"Обновляем счётчики за последние {days} дней")
parser.run(datetime.now(timezone.utc) - timedelta(days=days), which)
