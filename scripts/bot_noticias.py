import json
import os
import re
import html
import hashlib
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = "posts.json"

MAX_NOTICIAS_POR_FONTE = 5
MAX_POSTS = 200

HORAS_MAXIMO = 48

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)

FONTES = [
    {
        "nome": "GameVicio",
        "url": "https://www.gamevicio.com/noticias-sobre-games/",
        "categoria": "Notícia",
    },
    {
        "nome": "Xbox Wire",
        "url": "https://news.xbox.com/pt-br/",
        "categoria": "Xbox",
    },
]


# =========================================================
# DOWNLOAD DA PÁGINA
# =========================================================

def baixar_pagina(url):
    try:
        req = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            },
        )

        with urlopen(req, timeout=20) as resposta:
            dados = resposta.read()

            charset = resposta.headers.get_content_charset() or "utf-8"

            return dados.decode(charset, errors="ignore")

    except Exception as erro:
        print(f"Erro ao baixar {url}: {erro}")
        return ""


# =========================================================
# UTILIDADES
# =========================================================

def limpar_texto(texto):
    if not texto:
        return ""

    texto = html.unescape(texto)

    texto = re.sub(r"<[^>]+>", " ", texto)

    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def criar_id(titulo):
    texto = titulo.lower()

    texto = html.unescape(texto)

    texto = re.sub(r"[^a-z0-9áéíóúãõâêîôûç]+", "-", texto)

    texto = texto.strip("-")

    if not texto:
        texto = hashlib.md5(
            titulo.encode("utf-8")
        ).hexdigest()[:12]

    return texto[:100]


def data_atual():
    return datetime.now().strftime("%d/%m/%Y")


def noticia_recente(data_texto):
    """
    Tenta verificar se a notícia parece recente.
    Caso não consiga identificar a data, aceita.
    """

    if not data_texto:
        return True

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for formato in formatos:
        try:
            data = datetime.strptime(
                data_texto.strip(),
                formato
            )

            limite = datetime.now() - timedelta(
                hours=HORAS_MAXIMO
            )

            return data >= limite

        except ValueError:
            pass

    return True


# =========================================================
# EXTRAÇÃO DE IMAGEM
# =========================================================

def extrair_imagem(html_pagina, url_base):
    if not html_pagina:
        return ""

    # -----------------------------------------------------
    # Open Graph
    # -----------------------------------------------------

    padroes = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',

        r'<meta[^>]+property=["\']og:image:url["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image:url["\']',

        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]

    for padrao in padroes:
        resultado = re.search(
            padrao,
            html_pagina,
            re.IGNORECASE
        )

        if resultado:
            imagem = html.unescape(
                resultado.group(1)
            ).strip()

            imagem = urljoin(
                url_base,
                imagem
            )

            if imagem.startswith("http"):
                return imagem

    # -----------------------------------------------------
    # JSON-LD
    # -----------------------------------------------------

    imagens_json = re.findall(
        r'"image"\s*:\s*"([^"]+)"',
        html_pagina,
        re.IGNORECASE
    )

    for imagem in imagens_json:
        imagem = html.unescape(imagem)

        imagem = imagem.replace(
            "\\/",
            "/"
        )

        imagem = urljoin(
            url_base,
            imagem
        )

        if imagem.startswith("http"):
            return imagem

    # -----------------------------------------------------
    # Primeira imagem encontrada
    # -----------------------------------------------------

    imagens = re.findall(
        r'<img[^>]+(?:src|data-src)=["\']([^"\']+)',
        html_pagina,
        re.IGNORECASE
    )

    for imagem in imagens:
        imagem = html.unescape(
            imagem
        ).strip()

        imagem = urljoin(
            url_base,
            imagem
        )

        if (
            imagem.startswith("http")
            and not imagem.startswith(
                "https://www.google.com"
            )
            and not imagem.startswith(
                "https://news.google.com"
            )
        ):
            return imagem

    return ""


# =========================================================
# EXTRAÇÃO DE TÍTULOS/LINKS
# =========================================================

def extrair_links(html_pagina, url_base):
    resultados = []

    if not html_pagina:
        return resultados

    padrao = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )

    encontrados = padrao.findall(
        html_pagina
    )

    vistos = set()

    for link, conteudo in encontrados:

        link = html.unescape(link).strip()

        titulo = limpar_texto(conteudo)

        if not link:
            continue

        link = urljoin(
            url_base,
            link
        )

        if not link.startswith("http"):
            continue

        if link in vistos:
            continue

        vistos.add(link)

        if not titulo:
            continue

        resultados.append(
            {
                "titulo": titulo,
                "link": link,
            }
        )

    return resultados


# =========================================================
# FILTROS DE LINKS
# =========================================================

def link_valido(link, fonte):
    if not link:
        return False

    link_lower = link.lower()

    if fonte == "GameVicio":

        return (
            "gamevicio.com/noticias/" in link_lower
        )

    if fonte == "Xbox Wire":

        return (
            "news.xbox.com/pt-br/" in link_lower
            and link_lower.rstrip("/") !=
            "https://news.xbox.com/pt-br"
        )

    return False


# =========================================================
# FILTRO DE TÍTULOS
# =========================================================

def titulo_valido(titulo):
    if not titulo:
        return False

    titulo = titulo.strip()

    if len(titulo) < 10:
        return False

    if len(titulo) > 250:
        return False

    proibidos = [
        "privacy",
        "cookie",
        "subscribe",
        "newsletter",
        "login",
        "entrar",
        "registrar",
        "facebook",
        "instagram",
        "youtube",
        "twitter",
        "menu",
        "pesquisar",
        "search",
    ]

    titulo_lower = titulo.lower()

    for palavra in proibidos:
        if titulo_lower == palavra:
            return False

    return True


# =========================================================
# EXTRAIR RESUMO DA NOTÍCIA
# =========================================================

def extrair_resumo(html_pagina, titulo):
    if not html_pagina:
        return (
            f"Confira as principais informações sobre "
            f"{titulo}."
        )

    # Meta description
    padroes = [
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',

        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
    ]

    for padrao in padroes:

        resultado = re.search(
            padrao,
            html_pagina,
            re.IGNORECASE
        )

        if resultado:

            resumo = limpar_texto(
                resultado.group(1)
            )

            if len(resumo) > 30:

                if len(resumo) > 400:
                    resumo = resumo[:397] + "..."

                return resumo

    # Parágrafos
    paragrafos = re.findall(
        r"<p[^>]*>(.*?)</p>",
        html_pagina,
        re.IGNORECASE | re.DOTALL
    )

    for paragrafo in paragrafos:

        texto = limpar_texto(
            paragrafo
        )

        if (
            len(texto) >= 60
            and titulo.lower() not in texto.lower()
        ):

            if len(texto) > 400:
                texto = texto[:397] + "..."

            return texto

    return (
        f"Confira as principais informações sobre "
        f"{titulo}."
    )


# =========================================================
# CONTEÚDO DA NOTÍCIA
# =========================================================

def criar_conteudo(
    titulo,
    resumo,
    fonte,
    link
):

    return [
        resumo,

        (
            f"A notícia foi publicada originalmente "
            f"pelo site {fonte}."
        ),

        (
            f"O CavaloGameNews reúne as principais "
            f"informações para você acompanhar "
            f"as novidades do mundo dos games."
        ),

        f"🔗 Fonte: {link}",
    ]


# =========================================================
# CARREGAR POSTS
# =========================================================

def carregar_posts():

    if not os.path.exists(
        POSTS_FILE
    ):
        return []

    try:

        with open(
            POSTS_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

            if isinstance(
                dados,
                list
            ):
                return dados

    except Exception as erro:

        print(
            f"Erro ao ler posts.json: {erro}"
        )

    return []


# =========================================================
# SALVAR POSTS
# =========================================================

def salvar_posts(posts):

    with open(
        POSTS_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            posts,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

        arquivo.write(
            "\n"
        )


# =========================================================
# VERIFICAR DUPLICADA
# =========================================================

def noticia_ja_existe(
    posts,
    titulo,
    link
):

    titulo_lower = titulo.lower().strip()

    for post in posts:

        titulo_existente = str(
            post.get(
                "titulo",
                ""
            )
        ).lower().strip()

        link_existente = str(
            post.get(
                "link",
                ""
            )
        ).strip()

        if link and link == link_existente:
            return True

        if titulo_lower == titulo_existente:
            return True

    return False


# =========================================================
# PROCESSAR FONTE
# =========================================================

def processar_fonte(
    fonte,
    posts
):

    nome = fonte["nome"]
    url = fonte["url"]
    categoria = fonte["categoria"]

    print()
    print(
        "=" * 60
    )
    print(
        f"Fonte: {nome}"
    )
    print(
        f"URL: {url}"
    )
    print(
        "=" * 60
    )

    html_pagina = baixar_pagina(
        url
    )

    if not html_pagina:

        print(
            "Não foi possível acessar a fonte."
        )

        return 0

    links = extrair_links(
        html_pagina,
        url
    )

    print(
        f"Links encontrados: {len(links)}"
    )

    adicionadas = 0

    for item in links:

        if adicionadas >= MAX_NOTICIAS_POR_FONTE:
            break

        titulo = item["titulo"]
        link = item["link"]

        if not titulo_valido(
            titulo
        ):
            continue

        if not link_valido(
            link,
            nome
        ):
            continue

        if noticia_ja_existe(
            posts,
            titulo,
            link
        ):
            continue

        print()
        print(
            f"Nova notícia: {titulo}"
        )

        print(
            f"Link: {link}"
        )

        pagina_noticia = baixar_pagina(
            link
        )

        if not pagina_noticia:

            print(
                "Não foi possível abrir a notícia."
            )

            continue

        imagem = extrair_imagem(
            pagina_noticia,
            link
        )

        resumo = extrair_resumo(
            pagina_noticia,
            titulo
        )

        post_id = criar_id(
            titulo
        )

        # Evita colisão de ID
        ids_existentes = {
            str(
                p.get(
                    "id",
                    ""
                )
            )
            for p in posts
        }

        if post_id in ids_existentes:

            sufixo = hashlib.md5(
                link.encode(
                    "utf-8"
                )
            ).hexdigest()[:6]

            post_id = (
                f"{post_id}-{sufixo}"
            )

        novo_post = {
            "id": post_id,

            "titulo": titulo,

            "categoria": categoria,

            "data": data_atual(),

            "imagem": imagem,

            "resumo": resumo,

            "link": link,

            "x": "",

            "videos": [],

            "conteudo": criar_conteudo(
                titulo,
                resumo,
                nome,
                link
            ),
        }

        posts.insert(
            0,
            novo_post
        )

        adicionadas += 1

        print(
            "✓ Notícia adicionada!"
        )

        if imagem:

            print(
                f"✓ Imagem: {imagem}"
            )

        else:

            print(
                "⚠ Imagem não encontrada."
            )

    return adicionadas


# =========================================================
# PRINCIPAL
# =========================================================

def main():

    print()
    print(
        "=============================================="
    )
    print(
        "       BOT DE NOTÍCIAS - CAVALOGAMENEWS"
    )
    print(
        "=============================================="
    )

    posts = carregar_posts()

    print(
        f"Posts existentes: {len(posts)}"
    )

    total_novas = 0

    for fonte in FONTES:

        try:

            novas = processar_fonte(
                fonte,
                posts
            )

            total_novas += novas

        except Exception as erro:

            print()
            print(
                f"Erro na fonte {fonte['nome']}: {erro}"
            )

    # Limita quantidade total
    posts = posts[
        :MAX_POSTS
    ]

    salvar_posts(
        posts
    )

    print()
    print(
        "=============================================="
    )

    print(
        f"Novas notícias adicionadas: {total_novas}"
    )

    print(
        f"Total de posts: {len(posts)}"
    )

    print(
        "posts.json atualizado!"
    )

    print(
        "=============================================="
    )


if __name__ == "__main__":
    main()
