# -*- coding: utf-8 -*-
"""Сборщики постов: Telegram (открытая веб-версия t.me/s, без ключа) и ВКонтакте (API, нужен ключ)."""
import re, sys, time
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (career-posts research project)"}
now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def to_number(s):
    """'31.5K' -> 31500, '1.2M' -> 1200000, '246' -> 246."""
    s = (s or "").strip().replace(",", ".").replace(" ", "")
    if not s:
        return 0
    mult = {"K": 1_000, "M": 1_000_000}.get(s[-1].upper(), 1)
    try:
        return int(round(float(s[:-1] if mult > 1 else s) * mult))
    except ValueError:
        return 0


# ======================= Telegram =======================
def tg_media(msg):
    if msg.select_one(".tgme_widget_message_video_player, .tgme_widget_message_roundvideo_player"):
        return "video"
    photos = msg.select(".tgme_widget_message_photo_wrap")
    if len(photos) > 1 or msg.select_one(".tgme_widget_message_grouped_wrap"):
        return "album"
    if photos:
        return "photo"
    if msg.select_one(".tgme_widget_message_poll"):
        return "poll"
    if msg.select_one(".tgme_widget_message_document_wrap"):
        return "doc"
    return "text"


def tg_page(channel, before=None):
    url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
    for attempt in range(4):
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 429:                 # слишком часто — подождать
            time.sleep(5 * (attempt + 1)); continue
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    raise RuntimeError("Telegram не отвечает, попробуйте позже")


def collect_telegram(channel, company, since):
    soup = tg_page(channel)
    if not soup.select(".tgme_widget_message"):
        print(f"   ! Канал {channel} не найден или закрыт"); return []
    subs = 0
    for c in soup.select(".tgme_channel_info_counter"):
        if "subscriber" in c.get_text() or "подписчик" in c.get_text():
            subs = to_number(c.select_one(".counter_value").get_text())
    rows, seen = [], set()
    while True:
        msgs = soup.select(".tgme_widget_message[data-post]")
        if not msgs:
            break
        for m in msgs:
            pid = int(m["data-post"].split("/")[-1])
            if pid in seen:
                continue
            seen.add(pid)
            t = m.select_one("time[datetime]")
            if not t:
                continue
            dt = datetime.fromisoformat(t["datetime"]).astimezone(timezone.utc)
            if dt < since:
                continue
            text_el = m.select_one(".tgme_widget_message_text")
            reacts = sum(to_number(re.sub(r"[^\d.,KMkm]", "", r.get_text())) for r in m.select(".tgme_reaction"))
            rows.append({
                "platform": "telegram", "channel": channel, "company": company, "post_id": pid,
                "url": f"https://t.me/{channel}/{pid}", "date_utc": dt.strftime("%Y-%m-%d %H:%M"),
                "text": text_el.get_text("\n").strip() if text_el else "", "media": tg_media(m),
                "views": to_number((m.select_one(".tgme_widget_message_views") or BeautifulSoup("", "html.parser")).get_text()),
                "reactions": reacts, "likes": None, "reposts": None, "comments": None,
                "is_forward": int(bool(m.select_one(".tgme_widget_message_forwarded_from"))),
                "is_ad": 0, "is_pinned": 0, "subscribers": subs, "updated_utc": now(),
            })
        oldest = min(int(m["data-post"].split("/")[-1]) for m in msgs)
        oldest_dt = min(datetime.fromisoformat(t["datetime"]) for t in soup.select(".tgme_widget_message time[datetime]"))
        print(f"   {company} (Telegram): собрано {len(rows)} постов, дошли до {oldest_dt:%Y-%m-%d}")
        if oldest_dt.astimezone(timezone.utc) < since or oldest <= 1:
            break
        time.sleep(1.0)                           # бережём сайт
        soup = tg_page(channel, before=oldest)
    return rows


# ======================= ВКонтакте =======================
API, VERSION = "https://api.vk.com/method/", "5.199"


def vk(method, token, **params):
    params.update(access_token=token, v=VERSION)
    for attempt in range(5):
        r = requests.get(API + method, params=params, timeout=30).json()
        if "error" not in r:
            time.sleep(0.35)                      # не больше 3 запросов в секунду
            return r["response"]
        code, msg = r["error"].get("error_code"), r["error"].get("error_msg")
        if code == 6:
            time.sleep(1.5); continue
        if code == 5:
            sys.exit("Ключ ВКонтакте не подошёл. Проверьте, что скопировали его целиком, или выпустите новый.")
        if code in (15, 18, 30, 100):
            print(f"   ! Группа недоступна: {msg}"); return None
        sys.exit(f"Ошибка ВКонтакте {code}: {msg}")
    sys.exit("ВКонтакте слишком долго не отвечает.")


def vk_media(p):
    kinds = [a.get("type") for a in p.get("attachments", [])]
    if "video" in kinds or "clip" in kinds: return "video"
    if kinds.count("photo") > 1: return "album"
    if "photo" in kinds: return "photo"
    if "poll" in kinds: return "poll"
    if "doc" in kinds: return "doc"
    return "text"


def vk_row(p, domain, company, subs):
    likes, reposts, comments = (p.get(k, {}).get("count", 0) for k in ("likes", "reposts", "comments"))
    return {
        "platform": "vk", "channel": domain, "company": company, "post_id": p["id"],
        "url": f"https://vk.com/wall{p['owner_id']}_{p['id']}",
        "date_utc": datetime.fromtimestamp(p["date"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "text": p.get("text", ""), "media": vk_media(p),
        "views": p.get("views", {}).get("count"), "reactions": likes + reposts + comments,
        "likes": likes, "reposts": reposts, "comments": comments,
        "is_forward": int(bool(p.get("copy_history"))), "is_ad": int(bool(p.get("marked_as_ads"))),
        "is_pinned": int(bool(p.get("is_pinned"))), "subscribers": subs, "updated_utc": now(),
    }


def collect_vk(domain, company, token, since):
    info = vk("groups.getById", token, group_id=domain, fields="members_count")
    if not info:
        return []
    g = info["groups"][0] if isinstance(info, dict) else info[0]
    subs = g.get("members_count")
    rows, offset = [], 0
    while True:
        page = vk("wall.get", token, domain=domain, count=100, offset=offset)
        if not page or not page["items"]:
            break
        stop = False
        for p in page["items"]:
            if datetime.fromtimestamp(p["date"], tz=timezone.utc) < since:
                if p.get("is_pinned"):
                    continue                      # старый закреп пропускаем
                stop = True; break
            rows.append(vk_row(p, domain, company, subs))
        offset += 100
        print(f"   {company} (ВКонтакте): собрано {len(rows)} постов")
        if stop or offset >= page["count"]:
            break
    return rows
