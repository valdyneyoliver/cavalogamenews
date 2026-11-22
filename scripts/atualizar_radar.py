import json
import re
import hashlib
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
import feedparser
from deep_translator import GoogleTranslator

FEEDS = [
    ("Xbox Wire", "https://news.xbox.com/en-us/feed/"),
    ("PlayStation Blog", "https://blog.playstation.com/feed/"),
    ("Nintendo Life", "https://www.nintendolife.com/feeds/latest"),
    ("PC Gamer", "https://www.pcgamer.com/rss/"),
    ("Gematsu", "https://www.gematsu.com/feed"),
    ("VGC", "https://www.videogameschronicle.com/feed/"),
    ("Eurogamer", "https://www.eurogamer.net/feed"),
]
MAX_AGE_DAYS = 5
MAX_ITEMS = 60
OUT = Path("radar.json")

def clean_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"&nbsp;|&#160;", " ", value)
    value = re.sub(r"&amp;", "&", value)
    value = re.sub(r"&quot;", '"', value)
    value = re.sub(r"&#39;|&apos;", "'", value)
    return re.sub(r"\s+", " ", value).strip()

def published_date(entry):
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def platform_for(text):
    t = text.lower()
    found = []
    if any(x in t for x in ("xbox", "game pass", "series x", "series s", "microsoft gaming")):
        found.append("Xbox")
    if any(x in t for x in ("playstation", "ps5", "ps4", "sony interactive")):
        found.append("PlayStation")
    if any(x in t for x in ("nintendo", "switch 2", "switch")):
        found.append("Nintendo")
    if any(x in t for x in ("pc", "steam", "epic games", "windows", "nvidia", "amd", "graphics card")):
        found.append("PC")
    return " / ".join(found) if found else "Games"

def translate(text, limit=350):
    text = clean_html(text)[:limit]
    if not text:
        return ""
    try:
        return GoogleTranslator(source="auto", target="pt").translate(text) or text
    except Exception:
        return text

def main():
    translator = GoogleTranslator(source="auto", target="pt")
    del translator
    now = datetime.now(timezone.utc)
    seen = set()
    items = []
    for source, feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link", "").strip()
                title = clean_html(entry.get("title", ""))
                if not url.startswith(("https://", "http://")) or not title:
                    continue
                dt = published_date(entry)
                if now - dt > timedelta(days=MAX_AGE_DAYS):
                    continue
                key = hashlib.sha256(url.split("?")[0].encode()).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                summary = clean_html(raw_summary)
                if len(summary) < 45:
                    summary = title
                title_pt = translate(title, 220)
                summary_pt = translate(summary, 550)
                items.append({
                    "id": key[:16],
                    "titulo": title_pt,
                    "resumo": summary_pt,
                    "categoria": platform_for(title + " " + summary + " " + source),
                    "data": dt.isoformat(),
                    "fonte": source,
                    "url": url
                })
        except Exception as exc:
            print(f"Falha no feed {source}: {exc}")
    items.sort(key=lambda x: x["data"], reverse=True)
    OUT.write_text(json.dumps(items[:MAX_ITEMS], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Radar atualizado: {min(len(items), MAX_ITEMS)} notícias.")

if __name__ == "__main__":
    main()
