import json
import re
import html
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = "posts.json"

MAX_OFERTAS = 10
MAX_POSTS = 200

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/150 Safari/537.36"
    ),
    "Accept": (
        "application/rss+xml, application/xml, "
        "text/xml, text/html;q=0.9,*/*;q=0.8"
    ),
}


# =========================================================
# FONTES
# =========================================================

FONTES = [
    {
        "nome": "Epic Games",
        "url": "https://store.epicgames.com/en-US/feeds/free-games",
        "categoria": "Jogos Grátis",
    },
    {
        "nome": "GOG",
        "url": "https://www.gog.com/games?priceRange=0,0&order=desc:date",
        "categoria": "Jogos Grátis",
    },
]


# =========================================================
# BAIXAR CONTEÚDO
# =========================================================

def baixar(url):

    try:

        req = Request(
            url,
            headers=HEADERS
        )

        with urlopen(
            req,
            timeout=20
        ) as resposta:

            return resposta.read()

    except Exception as e:

        print(
            f"Erro ao acessar {url}: {e}"
        )

        return b""


# =========================================================
# TEXTO
# =========================================================

def texto_elemento(elemento):

    partes = []

    for texto in elemento.itertext():

        if texto:
            partes.append(texto)

    return " ".join(partes).strip()


def normalizar_texto(texto):

    texto = html.unescape(
        texto or ""
    )

    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# =========================================================
# SLUG
# =========================================================

def slug(texto):

    texto = normalizar_texto(
        texto
    ).lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for antigo, novo in substituicoes.items():

        texto = texto.replace(
            antigo,
            novo
        )

    texto = re.sub(
        r"[^a-z0-9]+",
        "-",
        texto
    )

    texto = texto.strip("-")

    return texto[:100]


def id_unico(titulo):

    data = datetime.now().strftime(
        "%Y%m%d"
    )

    return (
        f"{data}-{slug(titulo)}"
    )


# =========================================================
# POSTS.JSON
# =========================================================

def carregar_posts():

    try:

        with open(
            POSTS_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            posts = json.load(
                arquivo
            )

        if not isinstance(
            posts,
            list
        ):

            raise ValueError(
                "posts.json precisa conter uma lista."
            )

        return posts

    except FileNotFoundError:

        print(
            "posts.json não encontrado."
        )

        return []

    except Exception as e:

        print(
            f"Erro ao ler posts.json: {e}"
        )

        return []


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

    print(
        f"posts.json atualizado com {len(posts)} notícias."
    )


# =========================================================
# DUPLICADOS
# =========================================================

def normalizar_titulo(titulo):

    titulo = normalizar_texto(
        titulo
    ).lower()

    titulo = re.sub(
        r"[^a-z0-9à-ÿ ]+",
        "",
        titulo
    )

    titulo = re.sub(
        r"\s+",
        " ",
        titulo
    )

    return titulo.strip()


def ja_existe(
    titulo,
    link,
    posts
):

    titulo_normalizado = (
        normalizar_titulo(titulo)
    )

    link = (
        link or ""
    ).strip()

    for post in posts:

        titulo_antigo = normalizar_titulo(
            post.get(
                "titulo",
                ""
            )
        )

        link_antigo = (
            post.get(
                "link",
                ""
            )
            or ""
        ).strip()

        if (
            link
            and link_antigo
            and link == link_antigo
        ):

            return True

        if (
            titulo_normalizado
            and titulo_normalizado
            == titulo_antigo
        ):

            return True

    return False


# =========================================================
# RSS
# =========================================================

def encontrar_elemento(
    item,
    nomes
):

    for filho in list(item):

        tag = filho.tag

        if not isinstance(
            tag,
            str
        ):

            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag in nomes:

            return texto_elemento(
                filho
            )

    return ""


def encontrar_link(item):

    links = []

    for filho in list(item):

        tag = filho.tag

        if not isinstance(
            tag,
            str
        ):

            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag != "link":

            continue

        href = (
            filho.attrib
            .get(
                "href",
                ""
            )
            .strip()
        )

        if href:

            links.append(
                href
            )

        else:

            texto = texto_elemento(
                filho
            )

            if texto:

                links.append(
                    texto
                )

    # Evita links de comentários
    for link in links:

        if "/comments/" not in link.lower():

            return link.strip()

    return ""


# =========================================================
# IMAGEM
# =========================================================

def melhorar_imagem_blogger(url):

    if not url:

        return ""

    url = url.strip()

    if (
        "blogger.googleusercontent.com"
        not in url.lower()
    ):

        return url

    url = re.sub(
        r"/s\d+(?:-[^/]+)?/",
        "/s1600/",
        url,
        flags=re.I
    )

    return url


def encontrar_imagem(item):

    # media:content
    # media:thumbnail
    # enclosure

    for filho in item.iter():

        tag = filho.tag

        if not isinstance(
            tag,
            str
        ):

            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag in (
            "content",
            "thumbnail",
            "enclosure"
        ):

            url = (
                filho.attrib.get(
                    "url"
                )
                or filho.attrib.get(
                    "href"
                )
                or ""
            ).strip()

            tipo = (
                filho.attrib
                .get(
                    "type",
                    ""
                )
                .lower()
            )

            if url and (
                "image" in tipo
                or tag in (
                    "content",
                    "thumbnail"
                )
            ):

                return melhorar_imagem_blogger(
                    url
                )

    # Procura imagem dentro da descrição

    descricao = encontrar_elemento(
        item,
        {
            "description",
            "summary",
            "content"
        }
    )

    if descricao:

        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            descricao,
            flags=re.I
        )

        if match:

            return melhorar_imagem_blogger(
                html.unescape(
                    match.group(1)
                )
            )

    return ""


# =========================================================
# DATA
# =========================================================

def parsear_data(data_texto):

    if not data_texto:

        return datetime.now(
            timezone.utc
        )

    formatos = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]

    for formato in formatos:

        try:

            data = datetime.strptime(
                data_texto.strip(),
                formato
            )

            if data.tzinfo is None:

                data = data.replace(
                    tzinfo=timezone.utc
                )

            return data

        except ValueError:

            pass

    return datetime.now(
        timezone.utc
    )


# =========================================================
# BUSCAR RSS
# =========================================================

def buscar_rss(fonte):

    dados = baixar(
        fonte["url"]
    )

    if not dados:

        return []

    try:

        raiz = ET.fromstring(
            dados
        )

    except Exception as e:

        print(
            f"Erro no RSS de "
            f"{fonte['nome']}: {e}"
        )

        return []

    itens = []

    for item in raiz.iter():

        tag = item.tag

        if not isinstance(
            tag,
            str
        ):

            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag not in (
            "item",
            "entry"
        ):

            continue

        titulo = encontrar_elemento(
            item,
            {"title"}
        )

        link = encontrar_link(
            item
        )

        if not titulo or not link:

            continue

        resumo = encontrar_elemento(
            item,
            {
                "description",
                "summary",
                "content"
            }
        )

        data_texto = encontrar_elemento(
            item,
            {
                "pubdate",
                "published",
                "updated",
                "date",
                "dc:date"
            }
        )

        imagem = encontrar_imagem(
            item
        )

        data = parsear_data(
            data_texto
        )

        itens.append({
            "titulo": normalizar_texto(
                titulo
            ),
            "link": link,
            "resumo": normalizar_texto(
                resumo
            ),
            "imagem": imagem,
            "data_obj": data,
            "fonte": fonte["nome"],
            "categoria": fonte["categoria"],
        })

    return itens


# =========================================================
# IDENTIFICAR JOGOS GRÁTIS
# =========================================================

PALAVRAS_GRATIS = [
    "free",
    "grátis",
    "gratis",
    "gratuito",
    "gratuita",
    "free game",
    "free games",
    "free to keep",
    "giveaway",
    "give away",
]


def parece_gratis(oferta):

    texto = (
        oferta.get(
            "titulo",
            ""
        )
        + " "
        + oferta.get(
            "resumo",
            ""
        )
    ).lower()

    return any(
        palavra in texto
        for palavra in PALAVRAS_GRATIS
    )


def parece_jogo(titulo):

    palavras_excluir = [
        "dlc",
        "soundtrack",
        "pack",
        "bundle",
        "skin",
        "cosmetic",
        "demo",
        "trial",
        "expansion",
    ]

    titulo_lower = titulo.lower()

    return not any(
        palavra in titulo_lower
        for palavra in palavras_excluir
    )


# =========================================================
# RESUMO
# =========================================================

def criar_resumo(oferta):

    resumo = normalizar_texto(
        oferta.get(
            "resumo",
            ""
        )
    )

    if not resumo:

        return (
            f"{oferta['titulo']} "
            "está disponível gratuitamente "
            "por tempo limitado."
        )

    if len(resumo) > 300:

        resumo = (
            resumo[:297]
            .rsplit(
                " ",
                1
            )[0]
            + "..."
        )

    return resumo


# =========================================================
# CONTEÚDO
# =========================================================

def criar_conteudo(oferta):

    titulo = oferta["titulo"]
    fonte = oferta["fonte"]
    link = oferta["link"]
    resumo = criar_resumo(
        oferta
    )

    return [

        f"O jogo {titulo} "
        "está disponível gratuitamente "
        "por tempo limitado.",

        resumo,

        f"A oferta foi identificada "
        f"na {fonte}. O período de "
        "disponibilidade pode variar "
        "conforme a loja.",

        "Para conferir a oferta e "
        f"realizar o resgate, acesse "
        f"a página oficial: {link}"

    ]


# =========================================================
# CRIAR POST
# =========================================================

def criar_post(oferta):

    titulo = oferta["titulo"]

    return {

        "id": id_unico(
            titulo
        ),

        "titulo": titulo,

        "categoria": "Jogos Grátis",

        "data": datetime.now().strftime(
            "%d/%m/%Y"
        ),

        "imagem": oferta.get(
            "imagem",
            ""
        ),

        "resumo": criar_resumo(
            oferta
        ),

        "link": oferta["link"],

        "x": "",

        "videos": [],

        "conteudo": criar_conteudo(
            oferta
        )

    }


# =========================================================
# PRINCIPAL
# =========================================================

def main():

    print("=" * 60)

    print(
        "CavaloGameNews - Bot de Jogos Grátis"
    )

    print("=" * 60)

    posts = carregar_posts()

    ofertas = []

    for fonte in FONTES:

        print(
            f"\nConsultando: "
            f"{fonte['nome']}"
        )

        resultados = buscar_rss(
            fonte
        )

        print(
            f"Encontradas: "
            f"{len(resultados)}"
        )

        for oferta in resultados:

            if not parece_gratis(
                oferta
            ):

                continue

            if not parece_jogo(
                oferta["titulo"]
            ):

                continue

            if ja_existe(
                oferta["titulo"],
                oferta["link"],
                posts
            ):

                continue

            ofertas.append(
                oferta
            )

    # Mais recentes primeiro

    ofertas.sort(
        key=lambda x: x["data_obj"],
        reverse=True
    )

    ofertas = ofertas[
        :MAX_OFERTAS
    ]

    if not ofertas:

        print(
            "\nNenhum jogo grátis "
            "novo encontrado."
        )

        return

    novos_posts = []

    for oferta in ofertas:

        post = criar_post(
            oferta
        )

        novos_posts.append(
            post
        )

        print(
            f"\nNOVO: "
            f"{post['titulo']}"
        )

        print(
            f"Link: "
            f"{post['link']}"
        )

    # Notícias novas no começo

    posts = (
        novos_posts
        + posts
    )

    # Limite

    posts = posts[
        :MAX_POSTS
    ]

    salvar_posts(
        posts
    )

    print(
        f"\n{len(novos_posts)} "
        "jogo(s) grátis "
        "adicionado(s)."
    )

    print(
        "Pronto."
    )


if __name__ == "__main__":

    main()
