import json
import re
import hashlib
import time
import calendar

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from difflib import SequenceMatcher
from urllib.request import Request, urlopen

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
MAX_ITEMS = 25
MAX_PER_FEED = 8

OUT = Path("radar.json")

TRANSLATION_VERSION = 2
TRANSLATION_DELAY = 1.5

translation_blocked = False


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

    for key in (
        "published_parsed",
        "updated_parsed",
        "created_parsed"
    ):

        value = entry.get(key)

        if value:

            try:

                timestamp = calendar.timegm(value)

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

    # PRIORIDADE DA PUBLICAÇÃO

    if "Xbox" in source:
        return "Xbox"

    if "PlayStation" in source:
        return "PlayStation"

    if "Nintendo" in source:
        return "Nintendo"

    if "PC Gamer" in source:
        return "PC"

    if len(found) == 1:
        return found[0]

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
        "gta 6 guide",
        "gta 6 walkthrough",
    ]

    if any(word in text for word in unwanted):
        return False

    return True


# CARREGAR NOTÍCIAS ANTERIORES

def load_previous():

    if not OUT.exists():
        return {}

    try:

        previous = json.loads(
            OUT.read_text(encoding="utf-8")
        )

        return {
            item.get("url", "").split("?")[0].rstrip("/"): item
            for item in previous
            if item.get("url")
        }

    except Exception:

        return {}


# TRADUZIR TÍTULO E RESUMO JUNTOS

def translate_article(title, summary, previous=None):

    global translation_blocked

    # REAPROVEITAR TRADUÇÃO ANTERIOR

    if previous and previous.get("traducao_v") == TRANSLATION_VERSION:

        return (
            previous.get("titulo", title),
            previous.get("resumo", summary),
            True
        )

    if translation_blocked:

        return title, summary, False

    separator = "\n###RESUMO_CGN###\n"

    original = title + separator + summary

    print("Traduzindo notícia:", title[:70])

    try:

        # INTERVALO ENTRE SOLICITAÇÕES

        time.sleep(TRANSLATION_DELAY)

        translator = GoogleTranslator(
            source="auto",
            target="pt"
        )

        result = translator.translate(original)

        if not result or not result.strip():
            raise Exception("Tradução vazia.")

        result = result.strip()

        # SEPARAR TÍTULO E RESUMO

        if "###RESUMO_CGN###" not in result:

            raise Exception("Separador da tradução não encontrado.")

        title_pt, summary_pt = result.split(
            "###RESUMO_CGN###",
            1
        )

        title_pt = title_pt.strip()
        summary_pt = summary_pt.strip()

        if not title_pt or not summary_pt:
            raise Exception("Tradução incompleta.")

        return title_pt, summary_pt, True

    except Exception as exc:

        print("Erro na tradução:", exc)

        print("Pausando traduções nesta execução.")

        translation_blocked = True

        return title, summary, False


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

    previous_items = load_previous()

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

                if not is_news(title, summary):
                    continue

                if similar_title(title, seen_titles):
                    continue

                # RECUPERAR TRADUÇÃO ANTERIOR

                previous = previous_items.get(canonical_url)

                title_pt, summary_pt, translated = translate_article(
                    title,
                    summary,
                    previous
                )

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

                    "url": url,

                    "traducao_v": (
                        TRANSLATION_VERSION if translated else 0
                    )

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
