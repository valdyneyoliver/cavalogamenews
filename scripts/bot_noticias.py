#!/usr/bin/env python3
"""Publica no Discord apenas notícias novas do posts.json do CavaloGameNews.

Na primeira execução, registra as notícias que já existem sem publicá-las.
Nas execuções seguintes, envia somente IDs ainda não registrados.
O arquivo discord_posted.json precisa ser persistido no repositório pelo workflow.
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

POSTS_FILE = Path("posts.json")
STATE_FILE = Path("discord_posted.json")
BASE_URL = "https://cavalogamenews.com.br/noticias/"
MAX_PER_RUN = 10


def load_json(path, default):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def article_id(post):
    value = str(post.get("id", "")).strip()
    return value


def article_url(post):
    link = str(post.get("link", "")).strip()
    if link.startswith(("https://", "http://")):
        return link
    slug = article_id(post)
    return f"{BASE_URL}{slug}.html" if slug else "https://cavalogamenews.com.br/"


def send_to_discord(post, webhook):
    title = str(post.get("titulo") or "Nova notícia").strip()[:256]
    summary = str(post.get("resumo") or "Confira a notícia completa no site.").strip()
    category = str(post.get("categoria") or "Notícia").strip()[:256]
    date = str(post.get("data") or "").strip()
    url = article_url(post)
    image = str(post.get("imagem") or "").strip()

    embed = {
        "title": title,
        "url": url,
        "description": summary[:4096],
        "color": 0x00FF88,
        "fields": [{"name": "Categoria", "value": category or "Notícia", "inline": True}],
        "footer": {"text": "CavaloGameNews"},
    }
    if date:
        embed["fields"].append({"name": "Data", "value": date[:1024], "inline": True})
    if image.startswith(("https://", "http://")):
        embed["image"] = {"url": image}

    payload = json.dumps({"embeds": [embed]}, ensure_ascii=False).encode("utf-8")
    req = Request(webhook, data=payload, headers={"Content-Type": "application/json", "User-Agent": "CavaloGameNewsBot/1.0"}, method="POST")
    try:
        with urlopen(req, timeout=20) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord respondeu HTTP {response.status}")
        print(f"[OK] Enviada: {title}")
        return True
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        print(f"[ERRO] Discord HTTP {e.code}: {detail}")
    except (URLError, TimeoutError, RuntimeError) as e:
        print(f"[ERRO] Não foi possível enviar '{title}': {e}")
    return False


def main():
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("[ERRO] Configure o segredo DISCORD_WEBHOOK_URL no GitHub Actions.")
        return 1
    if not POSTS_FILE.exists():
        print("[ERRO] posts.json não encontrado na raiz do repositório.")
        return 1

    posts = load_json(POSTS_FILE, [])
    if not isinstance(posts, list):
        print("[ERRO] O posts.json precisa conter uma lista de notícias.")
        return 1

    valid_posts = [p for p in posts if isinstance(p, dict) and article_id(p)]
    ids_now = {article_id(p) for p in valid_posts}
    state = load_json(STATE_FILE, None)

    # Primeira execução: registrar a situação atual sem publicar o arquivo inteiro.
    if state is None:
        STATE_FILE.write_text(json.dumps(sorted(ids_now), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[INICIALIZAÇÃO] Registrei {len(ids_now)} notícias existentes sem enviá-las ao Discord.")
        print("[AÇÃO NECESSÁRIA] O workflow deve salvar discord_posted.json no repositório para manter o histórico entre execuções.")
        return 0

    if not isinstance(state, list):
        print("[ERRO] discord_posted.json inválido; não vou enviar para evitar duplicações.")
        return 1

    known = {str(x) for x in state}
    new_posts = [p for p in valid_posts if article_id(p) not in known]
    # posts.json costuma estar do mais novo para o mais antigo; envia as novas em ordem cronológica.
    new_posts = list(reversed(new_posts))[:MAX_PER_RUN]
    if not new_posts:
        print("[INFO] Nenhuma notícia nova para publicar.")
        return 0

    sent_ids = []
    for post in new_posts:
        if not send_to_discord(post, webhook):
            # Não marca a notícia que falhou; ela poderá ser tentada novamente.
            break
        sent_ids.append(article_id(post))

    known.update(sent_ids)
    STATE_FILE.write_text(json.dumps(sorted(known), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[RESUMO] Publicadas {len(sent_ids)} notícia(s) nova(s).")
    print("[AÇÃO NECESSÁRIA] O workflow deve fazer commit/push de discord_posted.json para preservar o histórico.")
    return 0 if len(sent_ids) == len(new_posts) else 1


if __name__ == "__main__":
    sys.exit(main())
