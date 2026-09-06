#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot automático de notícias do CavaloGameNews.

Fluxo:
1. Lê feeds RSS de notícias gamer.
2. Procura notícias publicadas recentemente.
3. Ignora duplicadas.
4. Resolve o link do Google News para a página da fonte original.
5. Busca a imagem SOMENTE na página original.
6. Cria a notícia no formato do posts.json.
7. Salva a notícia no início do posts.json.

IMPORTANTE:
- Nunca usa news.google.com como imagem.
- Nunca usa imagem hospedada pelo Google News.
- A imagem é buscada na página original da fonte.
- Se a fonte não fornecer uma imagem adequada, o campo "imagem"
  fica vazio em vez de usar uma imagem do Google.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
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

# Máximo de notícias novas por execução.
MAX_NEW_POSTS = 5

# Só considera notícias das últimas 48 horas.
MAX_AGE_HOURS = 48

# Limite de download da página original.
MAX_PAGE_BYTES = 3_000_000

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0 Safari/537.36 "
    "CavaloGameNewsBot/2.0"
)

# Google News é usado SOMENTE para descobrir notícias.
# A imagem NÃO é retirada do Google News.
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
# TEXTO
# =========================================================

def limpar_html(texto):
    if not texto:
        return ""

    texto = html.unescape(texto)
    texto = re.sub(
        r"(?is)<script.*?>.*?</script>",
        " ",
        texto,
    )
    texto = re.sub(
        r"(?is)<style.*?>.*?</style>",
        " ",
        texto,
    )
    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto,
    )
    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def normalizar_texto(texto):
    texto = texto or ""
    texto = normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = texto.lower()
    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto,
    )
    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def slugify(texto):
    texto = normalize("NFKD", texto)

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    texto = texto.lower()
    texto = re.sub(
        r"[^a-z0-9]+",
        "-",
        texto,
    )
    texto = re.sub(
        r"-+",
        "-",
        texto,
    )
    texto = texto.strip("-")

    return texto[:90] or "noticia"


def limitar_texto(texto, limite):
    texto = re.sub(
        r"\s+",
        " ",
        texto or "",
    ).strip()

    if len(texto) <= limite:
        return texto

    cortado = texto[:limite].rsplit(
        " ",
        1,
    )[0].strip()

    return cortado + " " + "..."


# =========================================================
# DATAS
# =========================================================

def extrair_data(item):
    datas = [
        item.findtext("pubDate"),
        item.findtext(
            "{http://purl.org/dc/elements/1.1/}date"
        ),
        item.findtext(
            "{http://www.w3.org/2005/Atom}published"
        ),
        item.findtext(
            "{http://www.w3.org/2005/Atom}updated"
        ),
    ]

    for valor in datas:
        if not valor:
            continue

        try:
            dt = parsedate_to_datetime(valor)

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                timezone.utc
            )

        except Exception:
            try:
                valor = valor.replace(
                    "Z",
                    "+00:00",
                )

                dt = datetime.fromisoformat(
                    valor
                )

                if dt.tzinfo is None:
                    dt = dt.replace(
                        tzinfo=timezone.utc
                    )

                return dt.astimezone(
                    timezone.utc
                )

            except Exception:
                pass

    return datetime.now(timezone.utc)


# =========================================================
# RSS
# =========================================================

def encontrar_texto(item, nomes):
    for nome in nomes:
        valor = item.findtext(nome)

        if valor and valor.strip():
            return valor.strip()

    return ""


def extrair_link(item):
    """
    Pega o link do RSS.

    Em feeds do Google News, esse link normalmente aponta
    para uma página de redirecionamento do Google News.
    Depois tentaremos resolver esse endereço para a fonte.
    """

    link = item.findtext("link")

    if link and link.strip():
        return link.strip()

    atom_link = item.find(
        "{http://www.w3.org/2005/Atom}link"
    )

    if atom_link is not None:
        href = atom_link.attrib.get(
            "href",
            "",
        )

        if href:
            return href.strip()

    return ""


def extrair_imagem_rss(item, descricao=""):
    """
    Não usamos essa imagem se ela vier do Google News.
    Ela só será aceita quando não for hospedada pelo Google.
    """

    namespaces = {
        "media": "http://search.yahoo.com/mrss/",
    }

    elementos = item.findall(
        "media:content",
        namespaces,
    )

    elementos += item.findall(
        "media:thumbnail",
        namespaces,
    )

    for elemento in elementos:
        url = elemento.attrib.get(
            "url",
            "",
        ).strip()

        if url and imagem_permitida(url):
            return url

    enclosure = item.find("enclosure")

    if enclosure is not None:
        tipo = enclosure.attrib.get(
            "type",
            "",
        )

        url = enclosure.attrib.get(
            "url",
            "",
        ).strip()

        if (
            url
            and (
                tipo.startswith("image/")
                or parece_imagem(url)
            )
            and imagem_permitida(url)
        ):
            return url

    # Só aceita imagem encontrada na descrição
    # se ela NÃO pertencer ao Google.
    match = re.search(
        r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']',
        descricao or "",
        flags=re.IGNORECASE,
    )

    if match:
        url = html.unescape(
            match.group(1)
        ).strip()

        if imagem_permitida(url):
            return url

    return ""


# =========================================================
# URL / IMAGEM
# =========================================================

def dominio(url):
    try:
        host = urllib.parse.urlparse(
            url
        ).netloc.lower()

        return host.replace(
            "www.",
            "",
        )

    except Exception:
        return ""


def eh_google(url):
    host = dominio(url)

    return (
        host == "google.com"
        or host.endswith(".google.com")
        or host == "googleusercontent.com"
        or host.endswith(".googleusercontent.com")
        or host == "gstatic.com"
        or host.endswith(".gstatic.com")
        or host == "news.google.com"
        or host.endswith(".news.google.com")
    )


def imagem_permitida(url):
    """
    Bloqueia imagens do Google.
    """

    if not url:
        return False

    if eh_google(url):
        return False

    if url.startswith("data:"):
        return False

    if url.lower().startswith(
        "javascript:"
    ):
        return False

    return True


def parece_imagem(url):
    if not url:
        return False

    url_sem_query = url.split(
        "?",
        1,
    )[0].lower()

    extensoes = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".avif",
    )

    return url_sem_query.endswith(
        extensoes
    )


def tornar_url_absoluta(
    url,
    base_url,
):
    if not url:
        return ""

    return urllib.parse.urljoin(
        base_url,
        url.strip(),
    )


# =========================================================
# RESOLVER LINK DA FONTE ORIGINAL
# =========================================================

def resolver_url_original(url):
    """
    Tenta seguir o redirecionamento do Google News.

    Se o endereço já for de uma fonte original,
    ele é mantido.
    """

    if not url:
        return ""

    # Se não for Google, já é uma fonte original.
    if not eh_google(url):
        return url

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": (
                    "pt-BR,pt;q=0.9,en;q=0.8"
                ),
            },
        )

        with urllib.request.urlopen(
            req,
            timeout=20,
        ) as resposta:

            final_url = resposta.geturl()

        if final_url and not eh_google(final_url):
            return final_url

    except Exception as erro:
        print(
            "[AVISO] Não foi possível resolver "
            "o link do Google News:"
        )
        print(
            f"        {erro}"
        )

    # Alguns links do Google News podem conter
    # a URL original codificada nos parâmetros.
    try:
        parsed = urllib.parse.urlparse(
            url
        )

        params = urllib.parse.parse_qs(
            parsed.query
        )

        for chave in (
            "url",
            "u",
            "link",
            "target",
        ):
            valores = params.get(
                chave,
                [],
            )

            for valor in valores:
                valor = urllib.parse.unquote(
                    valor
                )

                if (
                    valor.startswith("http")
                    and not eh_google(valor)
                ):
                    return valor

    except Exception:
        pass

    return url


# =========================================================
# PÁGINA ORIGINAL
# =========================================================

def baixar_pagina(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": (
                    "pt-BR,pt;q=0.9,en;q=0.8"
                ),
                "Referer": "https://www.google.com/",
            },
        )

        with urllib.request.urlopen(
            req,
            timeout=20,
        ) as resposta:

            dados = resposta.read(
                MAX_PAGE_BYTES
            )

            url_final = resposta.geturl()

            content_type = resposta.headers.get(
                "Content-Type",
                "",
            )

        if (
            "text/html"
            not in content_type.lower()
        ):
            return "", url_final

        return (
            dados.decode(
                "utf-8",
                errors="replace",
            ),
            url_final,
        )

    except Exception as erro:
        print(
            "[AVISO] Não foi possível abrir a página original:"
        )
        print(
            f"        {url}"
        )
        print(
            f"        {erro}"
        )

        return "", url


def extrair_meta(
    html_pagina,
    nome,
):
    """
    Procura meta tags como:

    property="og:image"
    content="..."

    ou:

    name="twitter:image"
    content="..."
    """

    if not html_pagina:
        return ""

    padroes = [
        rf'<meta[^>]+(?:property|name)\s*=\s*["\']{re.escape(nome)}["\'][^>]+content\s*=\s*["\']([^"\']+)["\']',
        rf'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]+(?:property|name)\s*=\s*["\']{re.escape(nome)}["\']',
    ]

    for padrao in padroes:
        match = re.search(
            padrao,
            html_pagina,
            flags=re.IGNORECASE,
        )

        if match:
            return html.unescape(
                match.group(1)
            ).strip()

    return ""


def extrair_imagem_pagina(
    html_pagina,
    url_pagina,
):
    """
    Procura SOMENTE na página original.

    Ordem:
    1. og:image
    2. og:image:url
    3. twitter:image
    4. twitter:image:src
    5. image_src
    6. imagem de <link>
    7. primeira imagem adequada
    """

    if not html_pagina:
        return ""

    metas = [
        "og:image",
        "og:image:url",
        "twitter:image",
        "twitter:image:src",
        "image_src",
    ]

    for nome in metas:
        imagem = extrair_meta(
            html_pagina,
            nome,
        )

        if not imagem:
            continue

        imagem = tornar_url_absoluta(
            imagem,
            url_pagina,
        )

        if imagem_permitida(
            imagem
        ):
            return imagem

    # link rel="image_src"
    matches = re.findall(
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        html_pagina,
        flags=re.IGNORECASE,
    )

    for imagem in matches:
        imagem = tornar_url_absoluta(
            html.unescape(imagem),
            url_pagina,
        )

        if imagem_permitida(
            imagem
        ):
            return imagem

    # Primeiras imagens da página.
    imagens = re.findall(
        r'<img[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
        html_pagina,
        flags=re.IGNORECASE,
    )

    for imagem in imagens:
        imagem = html.unescape(
            imagem
        ).strip()

        if not imagem:
            continue

        if imagem.startswith(
            "data:"
        ):
            continue

        if ".svg" in imagem.lower():
            continue

        if not imagem_permitida(
            imagem
        ):
            continue

        # Evita logos e elementos pequenos comuns.
        nome_imagem = imagem.lower()

        palavras_ignorar = [
            "logo",
            "icon",
            "avatar",
            "favicon",
            "pixel",
            "sprite",
            "tracking",
            "advert",
        ]

        if any(
            palavra in nome_imagem
            for palavra in palavras_ignorar
        ):
            continue

        imagem = tornar_url_absoluta(
            imagem,
            url_pagina,
        )

        if imagem_permitida(
            imagem
        ):
            return imagem

    return ""


def buscar_imagem_da_fonte(
    link,
    imagem_rss="",
):
    """
    NUNCA usa imagem do Google.

    Se o RSS fornecer uma imagem de outro domínio,
    ela pode ser utilizada.

    Caso contrário, resolve o link e abre a fonte original.
    """

    # 1. Imagem do RSS, mas somente se não for Google.
    if (
        imagem_rss
        and imagem_permitida(
            imagem_rss
        )
    ):
        print(
            "       [IMAGEM] Imagem do RSS "
            "é de fonte externa."
        )

        return imagem_rss

    # 2. Resolver para a página original.
    url_original = resolver_url_original(
        link
    )

    if not url_original:
        print(
            "       [IMAGEM] Não foi possível "
            "encontrar a fonte original."
        )

        return ""

    if eh_google(
        url_original
    ):
        print(
            "       [IMAGEM] Link continua "
            "no Google. Imagem ignorada."
        )

        return ""

    print(
        f"       [FONTE] {url_original}"
    )

    # 3. Abrir a página original.
    html_pagina, url_final = baixar_pagina(
        url_original
    )

    if not html_pagina:
        return ""

    # Garante que o redirecionamento final
    # também não seja Google.
    if eh_google(
        url_final
    ):
        print(
            "       [IMAGEM] Página final é "
            "do Google. Imagem ignorada."
        )

        return ""

    # 4. Procurar og:image/twitter:image etc.
    imagem = extrair_imagem_pagina(
        html_pagina,
        url_final,
    )

    if imagem and imagem_permitida(
        imagem
    ):
        print(
            f"       [IMAGEM] Original encontrada:"
        )
        print(
            f"       {imagem}"
        )

        return imagem

    print(
        "       [IMAGEM] A fonte não "
        "forneceu uma imagem adequada."
    )

    return ""


# =========================================================
# LER FEEDS
# =========================================================

def baixar_feed(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml,"
                " application/xml,"
                " text/xml"
            ),
            "Accept-Language": (
                "pt-BR,pt;q=0.9,en;q=0.8"
            ),
        },
    )

    with urllib.request.urlopen(
        req,
        timeout=30,
    ) as resposta:

        return resposta.read()


def ler_feed(feed):
    try:
        dados = baixar_feed(
            feed["url"]
        )

        raiz = ET.fromstring(
            dados
        )

    except Exception as erro:
        print(
            f"[AVISO] Não foi possível ler "
            f"{feed['nome']}: {erro}"
        )

        return []

    itens = []

    # RSS tradicional.
    for item in raiz.findall(
        ".//item"
    ):
        titulo = encontrar_texto(
            item,
            ["title"],
        )

        link = extrair_link(
            item
        )

        descricao = encontrar_texto(
            item,
            [
                "description",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
            ],
        )

        if not titulo or not link:
            continue

        imagem = extrair_imagem_rss(
            item,
            descricao,
        )

        data = extrair_data(
            item
        )

        itens.append(
            {
                "titulo": limpar_html(
                    titulo
                ),
                "link": link,
                "descricao": limpar_html(
                    descricao
                ),
                "imagem": imagem,
                "data": data,
                "feed": feed["nome"],
            }
        )

    # Atom.
    for item in raiz.findall(
        ".//{http://www.w3.org/2005/Atom}entry"
    ):
        titulo = encontrar_texto(
            item,
            [
                "{http://www.w3.org/2005/Atom}title"
            ],
        )

        link = extrair_link(
            item
        )

        descricao = encontrar_texto(
            item,
            [
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
            ],
        )

        if not titulo or not link:
            continue

        imagem = extrair_imagem_rss(
            item,
            descricao,
        )

        data = extrair_data(
            item
        )

        itens.append(
            {
                "titulo": limpar_html(
                    titulo
                ),
                "link": link,
                "descricao": limpar_html(
                    descricao
                ),
                "imagem": imagem,
                "data": data,
                "feed": feed["nome"],
            }
        )

    return itens


# =========================================================
# POSTS.JSON
# =========================================================

def carregar_posts():
    if not POSTS_FILE.exists():
        print(
            "[INFO] posts.json não existe. "
            "Criando novo arquivo."
        )

        return []

    try:
        with POSTS_FILE.open(
            "r",
            encoding="utf-8",
        ) as arquivo:

            posts = json.load(
                arquivo
            )

        if not isinstance(
            posts,
            list,
        ):
            raise ValueError(
                "posts.json precisa conter uma lista."
            )

        return posts

    except json.JSONDecodeError as erro:
        print(
            "[ERRO] O posts.json possui "
            "JSON inválido."
        )

        print(erro)

        sys.exit(1)


def salvar_posts(posts):
    with POSTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as arquivo:

        json.dump(
            posts,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

        arquivo.write("\n")


def noticia_ja_existe(
    item,
    posts,
):
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

    for post in posts:
        link_existente = str(
            post.get(
                "link",
                "",
            )
            or ""
        ).strip()

        if (
            link
            and link_existente
            and link == link_existente
        ):
            return True

        titulo_existente = normalizar_texto(
            str(
                post.get(
                    "titulo",
                    "",
                )
                or ""
            )
        )

        if (
            titulo
            and titulo_existente
            and titulo == titulo_existente
        ):
            return True

    return False


# =========================================================
# NOTÍCIA
# =========================================================

def criar_id(
    titulo,
    data,
    posts,
):
    base = (
        f"{data.strftime('%Y%m%d')}-"
        f"{slugify(titulo)}"
    )

    candidato = base
    contador = 2

    ids_existentes = {
        str(
            post.get(
                "id",
                "",
            )
        ).strip()
        for post in posts
    }

    while candidato in ids_existentes:
        candidato = (
            f"{base}-{contador}"
        )

        contador += 1

    return candidato


def criar_resumo(
    titulo,
    descricao,
):
    descricao = re.sub(
        r"\s+",
        " ",
        descricao or "",
    ).strip()

    if descricao:
        return limitar_texto(
            descricao,
            280,
        )

    return (
        f"{titulo} é uma das novidades "
        "recentes do mundo dos games."
    )


def criar_conteudo(
    titulo,
    resumo,
    link,
    fonte,
):
    conteudo = []

    conteudo.append(
        f"{titulo} foi destaque entre "
        "as novidades recentes do mundo "
        "dos videogames."
    )

    if resumo:
        conteudo.append(
            resumo
        )

    conteudo.append(
        f"A informação foi publicada "
        f"originalmente por {fonte}. "
        "O CavaloGameNews acompanha as "
        "novidades e reúne os principais "
        "detalhes disponíveis sobre o assunto."
    )

    conteudo.append(
        f"🔗 Fonte: {link}"
    )

    return conteudo


def encontrar_fonte(
    link,
    source_title="",
):
    try:
        dominio_fonte = dominio(
            link
        )

        if (
            dominio_fonte
            and dominio_fonte != "google.com"
            and "google" not in dominio_fonte
        ):
            return dominio_fonte

    except Exception:
        pass

    return source_title or "Fonte"


def categoria_da_noticia(
    titulo,
    resumo,
):
    texto = (
        f"{titulo} {resumo}"
    ).lower()

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


def extrair_nome_fonte_google_news(
    titulo,
):
    partes = re.split(
        r"\s+-\s+",
        titulo,
    )

    if len(partes) >= 2:
        return partes[-1].strip()

    return ""


def criar_post(
    item,
    posts,
):
    titulo = limpar_html(
        item.get(
            "titulo",
            "",
        )
    ).strip()

    link_google = item.get(
        "link",
        "",
    ).strip()

    descricao = limpar_html(
        item.get(
            "descricao",
            "",
        )
    ).strip()

    data = (
        item.get("data")
        or datetime.now(
            timezone.utc
        )
    )

    # Resolve o link antes de procurar imagem.
    link_original = resolver_url_original(
        link_google
    )

    if not link_original:
        link_original = link_google

    # Busca imagem SOMENTE na fonte original.
    imagem = buscar_imagem_da_fonte(
        link_original,
        item.get(
            "imagem",
            "",
        ),
    )

    # Fonte original.
    fonte = encontrar_fonte(
        link_original,
        item.get(
            "feed",
            "",
        ),
    )

    # Remove " - Nome da fonte" do título.
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

    post = {
        "id": criar_id(
            titulo_limpo,
            data,
            posts,
        ),
        "titulo": titulo_limpo,
        "categoria": categoria,
        "data": data.astimezone().strftime(
            "%d/%m/%Y"
        ),
        "imagem": imagem,
        "resumo": resumo,
        "link": link_original,
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
            link_original,
            fonte,
        ),
    }

    return post


# =========================================================
# PRINCIPAL
# =========================================================

def main():
    print("=" * 60)

    print(
        "CavaloGameNews - Bot automático "
        "de notícias v2.0"
    )

    print(
        "Imagem: SOMENTE fonte original"
    )

    print("=" * 60)

    posts = carregar_posts()

    print(
        f"[INFO] Notícias existentes: "
        f"{len(posts)}"
    )

    agora = datetime.now(
        timezone.utc
    )

    limite = (
        agora
        - timedelta(
            hours=MAX_AGE_HOURS
        )
    )

    noticias = []

    for feed in RSS_FEEDS:
        print(
            f"[INFO] Lendo: "
            f"{feed['nome']}"
        )

        for item in ler_feed(
            feed
        ):
            data = (
                item.get("data")
                or agora
            )

            if data < limite:
                continue

            if noticia_ja_existe(
                item,
                posts,
            ):
                continue

            noticias.append(
                item
            )

    noticias.sort(
        key=lambda item: (
            item.get("data")
            or agora
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

        if (
            link
            and link in links_vistos
        ):
            continue

        if (
            titulo
            and titulo in titulos_vistos
        ):
            continue

        links_vistos.add(
            link
        )

        titulos_vistos.add(
            titulo
        )

        selecionadas.append(
            item
        )

        if (
            len(selecionadas)
            >= MAX_NEW_POSTS
        ):
            break

    if not selecionadas:
        print(
            "[INFO] Nenhuma notícia "
            "nova encontrada."
        )

        print("=" * 60)

        return

    novos_posts = []

    for item in selecionadas:
        post = criar_post(
            item,
            posts,
        )

        novos_posts.append(
            post
        )

        print(
            f"[NOVO] {post['titulo']}"
        )

        print(
            f"       Categoria: "
            f"{post['categoria']}"
        )

        print(
            f"       Data: "
            f"{post['data']}"
        )

        print(
            f"       Imagem: "
            f"{post['imagem'] or 'NÃO ENCONTRADA'}"
        )

        print(
            f"       Link: "
            f"{post['link']}"
        )

    posts = (
        novos_posts
        + posts
    )

    salvar_posts(
        posts
    )

    print("-" * 60)

    print(
        f"[OK] {len(novos_posts)} "
        "notícia(s) adicionada(s)."
    )

    print(
        f"[OK] Total no posts.json: "
        f"{len(posts)}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
