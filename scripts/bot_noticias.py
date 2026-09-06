#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot automático de notícias do CavaloGameNews.

Fluxo:
1. Lê feeds RSS de notícias gamer.
2. Procura notícias publicadas recentemente.
3. Evita duplicadas usando link e título.
4. Busca automaticamente a imagem da página original.
5. Cria uma notícia no mesmo formato do posts.json.
6. Salva a notícia no início do posts.json.
7. O GitHub Actions executa gerar_noticias.py depois deste script.

IMPORTANTE:
- O bot usa título/descrição e imagem disponível na página original.
- Não copia artigos completos de outros sites.
- A imagem é procurada primeiro no RSS e depois na página original.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from unicodedata import normalize
import unicodedata


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = Path("posts.json")

# Quantas notícias novas podem ser adicionadas por execução.
MAX_NEW_POSTS = 5

# Só considera notícias publicadas nas últimas horas.
MAX_AGE_HOURS = 48

# User-Agent usado nas requisições.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0 Safari/537.36 "
    "CavaloGameNewsBot/1.1"
)

# Limite para não baixar páginas gigantes.
MAX_PAGE_BYTES = 3_000_000

# Feeds usando Google News RSS.
RSS_FEEDS = [
    {
        "nome": "Google News - Games",
        "url": (
            "https://news.google.com/rss/search?"
            "q=games+OR+videogames+OR+gaming"
            "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        ),
    },
    {
        "nome": "Google News - PlayStation Xbox Nintendo PC",
        "url": (
            "https://news.google.com/rss/search?"
            "q=PlayStation+OR+Xbox+OR+Nintendo+OR+PC+gaming"
            "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        ),
    },
    {
        "nome": "Google News - GTA Nintendo Direct Game Pass",
        "url": (
            "https://news.google.com/rss/search?"
            "q=GTA+OR+Nintendo+Direct+OR+Game+Pass+OR+Steam"
            "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        ),
    },
]


# =========================================================
# UTILITÁRIOS
# =========================================================

def limpar_html(texto):
    if not texto:
        return ""

    texto = html.unescape(texto)
    texto = re.sub(r"(?is)<script.*?>.*?</script>", " ", texto)
    texto = re.sub(r"(?is)<style.*?>.*?</style>", " ", texto)
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def normalizar_texto(texto):
    texto = texto or ""
    texto = normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def slugify(texto):
    texto = normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    texto = texto.strip("-")

    return texto[:90] or "noticia"


def limitar_texto(texto, limite):
    texto = re.sub(r"\s+", " ", texto or "").strip()

    if len(texto) <= limite:
        return texto

    cortado = texto[:limite].rsplit(" ", 1)[0].strip()
    return cortado + "..."


def extrair_data(item):
    datas = [
        item.findtext("pubDate"),
        item.findtext("{http://purl.org/dc/elements/1.1/}date"),
        item.findtext("{http://www.w3.org/2005/Atom}published"),
        item.findtext("{http://www.w3.org/2005/Atom}updated"),
    ]

    for valor in datas:
        if not valor:
            continue

        try:
            dt = parsedate_to_datetime(valor)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            try:
                valor = valor.replace("Z", "+00:00")
                dt = datetime.fromisoformat(valor)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

    return datetime.now(timezone.utc)


def encontrar_texto(item, nomes):
    for nome in nomes:
        valor = item.findtext(nome)
        if valor and valor.strip():
            return valor.strip()

    return ""


def extrair_link(item):
    link = item.findtext("link")

    if link and link.strip():
        return link.strip()

    atom_link = item.find("{http://www.w3.org/2005/Atom}link")
    if atom_link is not None:
        href = atom_link.attrib.get("href", "")
        if href:
            return href.strip()

    return ""


def extrair_imagem(item, descricao=""):
    """
    Tenta encontrar a imagem diretamente no RSS.
    """
    namespaces = {
        "media": "http://search.yahoo.com/mrss/",
    }

    # media:content
    elementos = item.findall("media:content", namespaces)
    elementos += item.findall("media:thumbnail", namespaces)

    for elemento in elementos:
        url = elemento.attrib.get("url", "").strip()

        if url and parece_imagem(url):
            return url

    # enclosure
    enclosure = item.find("enclosure")
    if enclosure is not None:
        tipo = enclosure.attrib.get("type", "")
        url = enclosure.attrib.get("url", "").strip()

        if url and (tipo.startswith("image/") or parece_imagem(url)):
            return url

    # Imagem dentro da descrição.
    match = re.search(
        r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']',
        descricao or "",
        flags=re.IGNORECASE,
    )

    if match:
        return html.unescape(match.group(1)).strip()

    return ""


def parece_imagem(url):
    if not url:
        return False

    url_sem_query = url.split("?", 1)[0].lower()

    extensoes = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".avif",
    )

    return url_sem_query.endswith(extensoes)


def tornar_url_absoluta(url, base_url):
    if not url:
        return ""

    return urllib.parse.urljoin(base_url, url.strip())


# =========================================================
# BUSCA DA IMAGEM NA PÁGINA ORIGINAL
# =========================================================

def baixar_pagina(url):
    """
    Baixa o HTML da página original.
    urllib.request segue redirecionamentos normalmente.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        )

        with urllib.request.urlopen(req, timeout=20) as resposta:
            dados = resposta.read(MAX_PAGE_BYTES)
            url_final = resposta.geturl()
            content_type = resposta.headers.get("Content-Type", "")

        if "text/html" not in content_type.lower():
            return "", url_final

        return dados.decode("utf-8", errors="replace"), url_final

    except Exception as erro:
        print(f"[AVISO] Não foi possível abrir a página para imagem: {url}")
        print(f"        {erro}")
        return "", url


def extrair_meta(html_pagina, nomes):
    """
    Procura:
    <meta property="og:image" content="...">
    <meta name="twitter:image" content="...">
    etc.
    """
    if not html_pagina:
        return ""

    for padrao in nomes:
        # content antes do atributo solicitado
        match = re.search(
            rf'<meta[^>]+(?:property|name)\s*=\s*["\']{re.escape(padrao)}["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
            html_pagina,
            flags=re.IGNORECASE,
        )

        if match:
            return html.unescape(match.group(1)).strip()

        # content antes de property/name
        match = re.search(
            rf'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]+(?:property|name)\s*=\s*["\']{re.escape(padrao)}["\']',
            html_pagina,
            flags=re.IGNORECASE,
        )

        if match:
            return html.unescape(match.group(1)).strip()

    return ""


def extrair_imagem_pagina(html_pagina, url_pagina):
    """
    Ordem de tentativa:
    1. og:image
    2. og:image:url
    3. twitter:image
    4. twitter:image:src
    5. image_src
    6. primeira imagem razoável do HTML
    """
    if not html_pagina:
        return ""

    nomes_meta = [
        "og:image",
        "og:image:url",
        "twitter:image",
        "twitter:image:src",
        "image_src",
    ]

    for nome in nomes_meta:
        imagem = extrair_meta(html_pagina, [nome])

        if imagem:
            return tornar_url_absoluta(
                imagem,
                url_pagina,
            )

    # Tenta encontrar uma imagem em link rel="image_src".
    match = re.search(
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        html_pagina,
        flags=re.IGNORECASE,
    )

    if match:
        return tornar_url_absoluta(
            html.unescape(match.group(1)),
            url_pagina,
        )

    # Último recurso: primeira imagem com src/data-src.
    imagens = re.findall(
        r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']',
        html_pagina,
        flags=re.IGNORECASE,
    )

    for imagem in imagens:
        imagem = html.unescape(imagem).strip()

        if not imagem:
            continue

        # Evita ícones, pixels e SVGs pequenos/óbvios.
        if imagem.startswith("data:"):
            continue

        if ".svg" in imagem.lower():
            continue

        if any(
            palavra in imagem.lower()
            for palavra in [
                "logo",
                "icon",
                "avatar",
                "favicon",
                "pixel",
                "sprite",
            ]
        ):
            continue

        return tornar_url_absoluta(
            imagem,
            url_pagina,
        )

    return ""


def buscar_imagem_automatica(item):
    """
    Primeiro usa a imagem do RSS.
    Se não existir, abre a página original e procura og:image.
    """
    imagem_rss = item.get("imagem", "").strip()

    if imagem_rss:
        print("       [IMAGEM] Encontrada no RSS.")
        return imagem_rss

    link = item.get("link", "").strip()

    if not link:
        print("       [IMAGEM] Sem link para procurar imagem.")
        return ""

    html_pagina, url_final = baixar_pagina(link)

    if not html_pagina:
        return ""

    imagem = extrair_imagem_pagina(
        html_pagina,
        url_final,
    )

    if imagem:
        print(f"       [IMAGEM] Encontrada: {imagem}")
    else:
        print("       [IMAGEM] Nenhuma imagem encontrada.")

    return imagem


# =========================================================
# RSS
# =========================================================

def baixar_feed(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, application/xml, text/xml"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        return resposta.read()


def ler_feed(feed):
    try:
        dados = baixar_feed(feed["url"])
        raiz = ET.fromstring(dados)
    except Exception as erro:
        print(f"[AVISO] Não foi possível ler {feed['nome']}: {erro}")
        return []

    itens = []

    # RSS tradicional
    for item in raiz.findall(".//item"):
        titulo = encontrar_texto(item, ["title"])
        link = extrair_link(item)

        descricao = encontrar_texto(
            item,
            [
                "description",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
            ],
        )

        if not titulo or not link:
            continue

        imagem = extrair_imagem(item, descricao)
        data = extrair_data(item)

        itens.append({
            "titulo": limpar_html(titulo),
            "link": link,
            "descricao": limpar_html(descricao),
            "imagem": imagem,
            "data": data,
            "feed": feed["nome"],
        })

    # Atom
    for item in raiz.findall(".//{http://www.w3.org/2005/Atom}entry"):
        titulo = encontrar_texto(
            item,
            ["{http://www.w3.org/2005/Atom}title"],
        )

        link = extrair_link(item)

        descricao = encontrar_texto(
            item,
            [
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
            ],
        )

        if not titulo or not link:
            continue

        imagem = extrair_imagem(item, descricao)
        data = extrair_data(item)

        itens.append({
            "titulo": limpar_html(titulo),
            "link": link,
            "descricao": limpar_html(descricao),
            "imagem": imagem,
            "data": data,
            "feed": feed["nome"],
        })

    return itens


# =========================================================
# POSTS.JSON
# =========================================================

def carregar_posts():
    if not POSTS_FILE.exists():
        print("[INFO] posts.json não existe. Criando um novo arquivo.")
        return []

    try:
        with POSTS_FILE.open("r", encoding="utf-8") as arquivo:
            posts = json.load(arquivo)

        if not isinstance(posts, list):
            raise ValueError("posts.json precisa conter uma lista.")

        return posts

    except json.JSONDecodeError as erro:
        print("[ERRO] O posts.json possui JSON inválido.")
        print(erro)
        sys.exit(1)


def salvar_posts(posts):
    with POSTS_FILE.open("w", encoding="utf-8") as arquivo:
        json.dump(
            posts,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )
        arquivo.write("\n")


def noticia_ja_existe(item, posts):
    link = item.get("link", "").strip()
    titulo = normalizar_texto(item.get("titulo", ""))

    for post in posts:
        link_existente = str(
            post.get("link", "") or ""
        ).strip()

        if link and link_existente and link == link_existente:
            return True

        titulo_existente = normalizar_texto(
            str(post.get("titulo", "") or "")
        )

        if titulo and titulo_existente and titulo == titulo_existente:
            return True

    return False


# =========================================================
# CRIAÇÃO DA NOTÍCIA
# =========================================================

def criar_id(titulo, data, posts):
    base = f"{data.strftime('%Y%m%d')}-{slugify(titulo)}"
    candidato = base
    contador = 2

    ids_existentes = {
        str(post.get("id", "")).strip()
        for post in posts
    }

    while candidato in ids_existentes:
        candidato = f"{base}-{contador}"
        contador += 1

    return candidato


def criar_resumo(titulo, descricao):
    descricao = re.sub(
        r"\s+",
        " ",
        descricao or "",
    ).strip()

    if descricao:
        return limitar_texto(descricao, 280)

    return (
        f"{titulo} é uma das novidades recentes "
        "do mundo dos games."
    )


def criar_conteudo(titulo, resumo, link, fonte):
    conteudo = []

    conteudo.append(
        f"{titulo} foi destaque entre as novidades recentes "
        "do mundo dos videogames."
    )

    if resumo:
        conteudo.append(resumo)

    conteudo.append(
        f"A informação foi publicada originalmente por {fonte}. "
        "O CavaloGameNews acompanha as novidades e reúne os "
        "principais detalhes disponíveis sobre o assunto."
    )

    conteudo.append(
        f"🔗 Fonte: {link}"
    )

    return conteudo


def criar_post(item, posts):
    titulo = limpar_html(
        item.get("titulo", "")
    ).strip()

    link = item.get("link", "").strip()

    descricao = limpar_html(
        item.get("descricao", "")
    ).strip()

    data = item.get("data") or datetime.now(timezone.utc)

    # Busca a imagem automaticamente.
    imagem = buscar_imagem_automatica(item)

    fonte_google = extrair_nome_fonte_google_news(titulo)

    # Remove o nome da fonte do final do título quando
    # o Google News usar o formato:
    # "Título da notícia - Site"
    titulo_limpo = re.sub(
        r"\s+-\s+[^-]+$",
        "",
        titulo,
    ).strip()

    if not titulo_limpo:
        titulo_limpo = titulo

    resumo = criar_resumo(
        titulo_limpo,
        descricao,
    )

    categoria = categoria_da_noticia(
        titulo_limpo,
        resumo,
    )

    fonte = (
        fonte_google
        or encontrar_fonte(
            link,
            item.get("feed", ""),
        )
    )

    post = {
        "id": criar_id(
            titulo_limpo,
            data,
            posts,
        ),
        "titulo": titulo_limpo,
        "categoria": categoria,
        "data": data.astimezone().strftime("%d/%m/%Y"),
        "imagem": imagem,
        "resumo": resumo,
        "link": link,
        "x": "",
        "videos": [
            {
                "tipo": "youtube",
                "url": "xxx",
            }
        ],
        "conteudo": criar_conteudo(
            titulo_limpo,
            resumo,
            link,
            fonte,
        ),
    }

    return post


def encontrar_fonte(link, source_title=""):
    try:
        dominio = urllib.parse.urlparse(
            link
        ).netloc.lower()

        dominio = dominio.replace(
            "www.",
            "",
        )

        if dominio:
            return dominio

    except Exception:
        pass

    return source_title or "Fonte"


def categoria_da_noticia(titulo, resumo):
    texto = f"{titulo} {resumo}".lower()

    regras = [
        (
            "Xbox",
            [
                "xbox",
                "game pass",
                "cloud gaming",
                "series x",
                "series s",
                "microsoft",
            ],
        ),
        (
            "PlayStation",
            [
                "playstation",
                "ps5",
                "ps4",
                "sony",
                "state of play",
            ],
        ),
        (
            "Nintendo",
            [
                "nintendo",
                "switch",
                "zelda",
                "mario",
                "pokemon",
            ],
        ),
        (
            "Pc",
            [
                "pc",
                "steam",
                "epic games",
                "nvidia",
                "amd",
                "windows",
                "dlss",
            ],
        ),
    ]

    for categoria, palavras in regras:
        if any(
            palavra in texto
            for palavra in palavras
        ):
            return categoria

    return "Notícias"


def extrair_nome_fonte_google_news(titulo):
    partes = re.split(
        r"\s+-\s+",
        titulo,
    )

    if len(partes) >= 2:
        return partes[-1].strip()

    return ""


# =========================================================
# PRINCIPAL
# =========================================================

def main():
    print("=" * 60)
    print("CavaloGameNews - Bot automático de notícias")
    print("=" * 60)

    posts = carregar_posts()

    print(
        f"[INFO] Notícias existentes: {len(posts)}"
    )

    agora = datetime.now(timezone.utc)

    limite = agora - timedelta(
        hours=MAX_AGE_HOURS
    )

    noticias = []

    for feed in RSS_FEEDS:
        print(
            f"[INFO] Lendo: {feed['nome']}"
        )

        for item in ler_feed(feed):
            data = item.get("data") or agora

            if data < limite:
                continue

            if noticia_ja_existe(
                item,
                posts,
            ):
                continue

            noticias.append(item)

    noticias.sort(
        key=lambda item: (
            item.get("data") or agora
        ),
        reverse=True,
    )

    selecionadas = []

    links_vistos = set()
    titulos_vistos = set()

    for item in noticias:
        link = item.get(
            "link",
            "",
        ).strip()

        titulo = normalizar_texto(
            item.get(
                "titulo",
                "",
            )
        )

        if link and link in links_vistos:
            continue

        if titulo and titulo in titulos_vistos:
            continue

        links_vistos.add(link)
        titulos_vistos.add(titulo)

        selecionadas.append(item)

        if len(selecionadas) >= MAX_NEW_POSTS:
            break

    if not selecionadas:
        print(
            "[INFO] Nenhuma notícia nova encontrada."
        )

        print("=" * 60)
        return

    novos_posts = []

    for item in selecionadas:
        post = criar_post(
            item,
            posts,
        )

        novos_posts.append(post)

        print(
            f"[NOVO] {post['titulo']}"
        )

        print(
            f"       Categoria: {post['categoria']}"
        )

        print(
            f"       Data: {post['data']}"
        )

        print(
            f"       Imagem: "
            f"{post['imagem'] or 'NÃO ENCONTRADA'}"
        )

        print(
            f"       Link: {post['link']}"
        )

    posts = novos_posts + posts

    salvar_posts(posts)

    print("-" * 60)

    print(
        f"[OK] {len(novos_posts)} notícia(s) adicionada(s)."
    )

    print(
        f"[OK] Total no posts.json: {len(posts)}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
