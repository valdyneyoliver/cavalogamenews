import json
import re
import hashlib
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from difflib import SequenceMatcher
from urllib.request import Request, urlopen

import feedparser
from deep_translator import GoogleTranslator, MyMemoryTranslator


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
MAX_ITEMS = 35
MAX_PER_FEED = 12

OUT = Path("radar.json")

cache_traducao = {}


# LIMPAR HTML

def clean_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"&nbsp;|&#160;", " ", value)
    value = re.sub(r"&amp;", "&", value)
    value = re.sub(r"&quot;", '"', value)
    value = re.sub(r"&#39;|&apos;", "'", value)

    return re.sub(r"\s+", " ", value).strip()


# DATA DA NOTÍCIA

def published_date(entry):

    for key in ("published_parsed", "updated_parsed", "created_parsed"):

        value = entry.get(key)

        if value:
            try:
                from time import mktime

                timestamp = mktime(value)

                return datetime.fromtimestamp(
                    timestamp,
                    timezone.utc
                )

            except Exception:
                pass

    for key in ("published", "updated", "created"):

        raw = entry.get(key)

        if raw:
            try:
                dt = parsedate_to_datetime(raw)

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt.astimezone(timezone.utc)

            except Exception:
                try:
                    dt = datetime.fromisoformat(
                        raw.replace("Z", "+00:00")
                    )

                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)

                    return dt.astimezone(timezone.utc)

                except Exception:
                    pass

    return None


# IDENTIFICAR PLATAFORMA

def platform_for(text, source):

    t = text.lower()

    found = []

    if any(x in t for x in (
        "xbox",
        "game pass",
        "series x",
        "series s",
        "microsoft gaming"
    )):
        found.append("Xbox")

    if any(x in t for x in (
        "playstation",
        "ps5",
        "ps4",
        "sony interactive"
    )):
        found.append("PlayStation")

    if any(x in t for x in (
        "nintendo",
        "switch 2",
        "switch"
    )):
        found.append("Nintendo")

    if any(x in t for x in (
        "pc",
        "steam",
        "epic games",
        "windows",
        "nvidia",
        "amd",
        "graphics card"
    )):
        found.append("PC")

    # Prioridade para a plataforma da própria publicação

    if "Xbox" in source:
        return "Xbox"

    if "PlayStation" in source:
        return "PlayStation"

    if "Nintendo" in source:
        return "Nintendo"

    if "PC Gamer" in source:
        return "PC"

    # Se houver apenas uma plataforma identificada

    if len(found) == 1:
        return found[0]

    # Se houver várias plataformas

    if len(found) > 1:
        return "Multiplataforma"

    return "Notícias"


# FILTRAR CONTEÚDO QUE NÃO É NOTÍCIA

def is_news(title, summary):

    text = (title + " " + summary).lower()

    unwanted = [
        "how to",
        "guide:",
        "walkthrough",
        "review:",
        "review –",
        "opinion:",
        "best games",
        "top 10",
        "tier list",
        "poll:",
        "quiz:",
        "tips and tricks",
        "everything you need to know",
        "complete guide",
        "buying guide",
    ]

    if any(word in text for word in unwanted):
        return False

    return True


# TRADUÇÃO

def translate(text, limit=500):

    text = clean_html(text)[:limit]

    if not text:
        return ""

    if text in cache_traducao:
        return cache_traducao[text]

    # Primeira tentativa: Google Tradutor

    for attempt in range(2):

        try:
            translator = GoogleTranslator(
                source="auto",
                target="pt"
            )

            result = translator.translate(text)

            if result and result.strip():

                result = result.strip()

                cache_traducao[text] = result

                time.sleep(0.4)

                return result

        except Exception as exc:

            print(f"Google Tradutor: {exc}")

            time.sleep(2)

    # Segunda tentativa: MyMemory

    try:

        translator = MyMemoryTranslator(
            source="en-US",
            target="pt-BR"
        )

        result = translator.translate(text)

        if result and result.strip():

            result = result.strip()

            cache_traducao[text] = result

            time.sleep(0.4)

            return result

    except Exception as exc:

        print(f"MyMemory: {exc}")

    print("Aviso: não foi possível traduzir:", text[:70])

    return text


# EVITAR NOTÍCIAS REPETIDAS

def similar_title(title, existing):

    normalized = re.sub(
        r"[^a-z0-9 ]",
        "",
        title.lower()
    )

    for old in existing:

        old_normalized = re.sub(
            r"[^a-z0-9 ]",
            "",
            old.lower()
        )

        similarity = SequenceMatcher(
            None,
            normalized,
            old_normalized
        ).ratio()

        if similarity >= 0.82:
            return True

    return False


# BUSCAR FEED

def get_feed(url):

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 CavaloGameNews Radar"
        }
    )

    with urlopen(request, timeout=25) as response:

        content = response.read()

    return feedparser.parse(content)


# PROCESSAMENTO PRINCIPAL

def main():

    now = datetime.now(timezone.utc)

    seen_urls = set()
    seen_titles = []

    items = []

    for source, feed_url in FEEDS:

        print(f"\nBuscando: {source}")

        try:

            feed = get_feed(feed_url)

            feed_count = 0

            for entry in feed.entries:

                if feed_count >= MAX_PER_FEED:
                    break

                url = entry.get("link", "").strip()

                title = clean_html(
                    entry.get("title", "")
                )

                if not url.startswith(("https://", "http://")):
                    continue

                if not title:
                    continue

                dt = published_date(entry)

                if not dt:
                    print("Notícia ignorada: sem data válida.")
                    continue

                if dt > now + timedelta(hours=12):
                    continue

                if now - dt > timedelta(days=MAX_AGE_DAYS):
                    continue

                canonical_url = url.split("?")[0].rstrip("/")

                key = hashlib.sha256(
                    canonical_url.encode()
                ).hexdigest()

                if key in seen_urls:
                    continue

                raw_summary = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                )

                summary = clean_html(raw_summary)

                if len(summary) < 45:
                    summary = title

                # FILTRAR GUIAS E CONTEÚDOS REPETITIVOS

                if not is_news(title, summary):
                    continue

                # EVITAR TÍTULOS MUITO PARECIDOS

                if similar_title(title, seen_titles):
                    continue

                print("Traduzindo:", title[:80])

                title_pt = translate(title, 220)

                summary_pt = translate(summary, 500)

                category = platform_for(
                    title + " " + summary,
                    source
                )

                items.append({

                    "id": key[:16],

                    "titulo": title_pt,

                    "resumo": summary_pt,

                    "categoria": category,

                    "data": dt.isoformat(),

                    "fonte": source,

                    "url": url

                })

                seen_urls.add(key)

                seen_titles.append(title)

                feed_count += 1

        except Exception as exc:

            print(f"Falha no feed {source}: {exc}")

    # ORDENAR POR DATA

    items.sort(
        key=lambda x: x["data"],
        reverse=True
    )

    # SALVAR RADAR

    OUT.write_text(
        json.dumps(
            items[:MAX_ITEMS],
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\n-----------------------------")

    print(
        f"Radar atualizado: {min(len(items), MAX_ITEMS)} notícias."
    )

    print("-----------------------------")


if __name__ == "__main__":
    main()
