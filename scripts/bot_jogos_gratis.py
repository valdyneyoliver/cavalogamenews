import json
import re
import html
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote


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
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}


# =========================================================
# BAIXAR
# =========================================================

def baixar(url):

    try:

        req = Request(
            url,
            headers=HEADERS
        )

        with urlopen(
            req,
            timeout=30
        ) as resposta:

            return resposta.read()

    except Exception as e:

        print(
            f"Erro ao acessar:\n{url}\n{e}"
        )

        return b""


def baixar_json(url):

    dados = baixar(url)

    if not dados:
        return None

    try:

        return json.loads(
            dados.decode(
                "utf-8"
            )
        )

    except Exception as e:

        print(
            f"Erro ao interpretar JSON: {e}"
        )

        return None


# =========================================================
# TEXTO
# =========================================================

def limpar_texto(texto):

    texto = html.unescape(
        str(texto or "")
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

    texto = limpar_texto(
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

    return texto.strip("-")[:100]


def criar_id(titulo):

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
                "posts.json precisa ser uma lista."
            )

        return posts

    except FileNotFoundError:

        print(
            "posts.json não encontrado."
        )

        return []

    except Exception as e:

        print(
            f"Erro ao abrir posts.json: {e}"
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
        f"posts.json salvo com {len(posts)} posts."
    )


# =========================================================
# DUPLICADOS
# =========================================================

def normalizar_titulo(titulo):

    titulo = limpar_texto(
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

    titulo = normalizar_titulo(
        titulo
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
            titulo
            and titulo == titulo_antigo
        ):

            return True

    return False


# =========================================================
# EPIC GAMES
# =========================================================

EPIC_API = (
    "https://store-site-backend-static.ak.epicgames.com/"
    "freeGamesPromotions"
    "?locale=pt-BR"
    "&country=BR"
    "&allowCountries=BR"
)


def buscar_epic():

    print(
        "\nConsultando Epic Games..."
    )

    dados = baixar_json(
        EPIC_API
    )

    if not dados:

        print(
            "Epic Games: nenhum dado recebido."
        )

        return []

    resultado = []

    try:

        elementos = (
            dados
            .get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )

        for jogo in elementos:

            titulo = limpar_texto(
                jogo.get(
                    "title",
                    ""
                )
            )

            if not titulo:
                continue

            promocoes = jogo.get(
                "promotions"
            )

            if not promocoes:
                continue

            ofertas = (
                promocoes.get(
                    "promotionalOffers",
                    []
                )
            )

            futuras = (
                promocoes.get(
                    "upcomingPromotionalOffers",
                    []
                )
            )

            ofertas_validas = []

            for grupo in ofertas:

                for oferta in grupo.get(
                    "promotionalOffers",
                    []
                ):

                    desconto = oferta.get(
                        "discountSetting",
                        {}
                    )

                    desconto_percentual = (
                        desconto.get(
                            "discountPercentage"
                        )
                    )

                    if desconto_percentual == 0:

                        ofertas_validas.append(
                            oferta
                        )

            if not ofertas_validas:

                continue

            descricao = limpar_texto(
                jogo.get(
                    "description",
                    ""
                )
            )

            slug_epic = jogo.get(
                "productSlug"
            )

            url = ""

            if slug_epic:

                url = (
                    "https://store.epicgames.com/"
                    "pt-BR/p/"
                    + str(slug_epic)
                )

            if not url:

                url = (
                    "https://store.epicgames.com/"
                    "pt-BR/"
                )

            imagem = ""

            imagens = jogo.get(
                "keyImages",
                []
            )

            for imagem_item in imagens:

                imagem_url = imagem_item.get(
                    "url",
                    ""
                )

                if imagem_url:

                    imagem = imagem_url
                    break

            resultado.append({

                "titulo": titulo,

                "resumo": (
                    descricao
                    or
                    f"{titulo} está "
                    "gratuito por tempo limitado "
                    "na Epic Games Store."
                ),

                "link": url,

                "imagem": imagem,

                "loja": "Epic Games",

            })

        print(
            f"Epic Games: "
            f"{len(resultado)} jogo(s) grátis encontrado(s)."
        )

    except Exception as e:

        print(
            f"Erro processando Epic Games: {e}"
        )

    return resultado


# =========================================================
# GOG
# =========================================================

GOG_API = (
    "https://catalog.gog.com/v1/catalog"
    "?limit=48"
    "&price=between%3A0%2C0"
    "&order=desc%3Atrending"
    "&productType=in%3Agame"
    "&page=1"
    "&countryCode=BR"
    "&locale=pt-BR"
    "&currencyCode=BRL"
)


def buscar_gog():

    print(
        "\nConsultando GOG..."
    )

    dados = baixar_json(
        GOG_API
    )

    if not dados:

        print(
            "GOG: nenhum dado recebido."
        )

        return []

    resultado = []

    try:

        produtos = []

        if isinstance(
            dados,
            dict
        ):

            produtos = (
                dados.get(
                    "products",
                    []
                )
            )

            if not produtos:

                produtos = (
                    dados.get(
                        "product",
                        []
                    )
                )

        for jogo in produtos:

            titulo = limpar_texto(
                jogo.get(
                    "title",
                    ""
                )
            )

            if not titulo:
                continue

            # Evita demos e DLCs

            texto_titulo = titulo.lower()

            if any(
                palavra in texto_titulo
                for palavra in [
                    "demo",
                    "dlc",
                    "soundtrack",
                    "prologue"
                ]
            ):

                continue

            slug_gog = (
                jogo.get(
                    "slug"
                )
                or
                jogo.get(
                    "url"
                )
            )

            if not slug_gog:
                continue

            if str(
                slug_gog
            ).startswith(
                "http"
            ):

                url = str(
                    slug_gog
                )

            else:

                url = (
                    "https://www.gog.com/"
                    "game/"
                    + str(slug_gog)
                )

            imagem = ""

            for chave in [
                "image",
                "coverHorizontal",
                "cover"
            ]:

                valor = jogo.get(
                    chave
                )

                if isinstance(
                    valor,
                    str
                ) and valor:

                    imagem = valor
                    break

            resultado.append({

                "titulo": titulo,

                "resumo": (
                    f"{titulo} está "
                    "disponível gratuitamente "
                    "na GOG."
                ),

                "link": url,

                "imagem": imagem,

                "loja": "GOG",

            })

        print(
            f"GOG: "
            f"{len(resultado)} jogo(s) grátis encontrado(s)."
        )

    except Exception as e:

        print(
            f"Erro processando GOG: {e}"
        )

    return resultado


# =========================================================
# CRIAR CONTEÚDO
# =========================================================

def criar_conteudo(oferta):

    titulo = oferta["titulo"]
    loja = oferta["loja"]
    link = oferta["link"]

    resumo = limpar_texto(
        oferta.get(
            "resumo",
            ""
        )
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

    return [

        f"O jogo {titulo} "
        f"está disponível gratuitamente "
        f"na {loja}.",

        resumo,

        "A oferta pode ficar disponível "
        "por tempo limitado, então vale "
        "a pena conferir o período de "
        "resgate diretamente na loja.",

        f"Para resgatar o jogo, acesse "
        f"a página oficial: {link}"

    ]


# =========================================================
# CRIAR POST
# =========================================================

def criar_post(oferta):

    titulo = oferta["titulo"]

    return {

        "id": criar_id(
            titulo
        ),

        "titulo": (
            f"{titulo} está grátis "
            f"por tempo limitado"
        ),

        "categoria": "Jogos Grátis",

        "data": datetime.now().strftime(
            "%d/%m/%Y"
        ),

        "imagem": oferta.get(
            "imagem",
            ""
        ),

        "resumo": limpar_texto(
            oferta.get(
                "resumo",
                ""
            )
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
        "CavaloGameNews"
    )

    print(
        "Bot de Jogos Grátis"
    )

    print("=" * 60)

    posts = carregar_posts()

    ofertas = []

    # Epic

    ofertas.extend(
        buscar_epic()
    )

    # GOG

    ofertas.extend(
        buscar_gog()
    )

    print(
        f"\nTotal encontrado: "
        f"{len(ofertas)}"
    )

    novos = []

    for oferta in ofertas:

        if ja_existe(
            oferta["titulo"],
            oferta["link"],
            posts
        ):

            print(
                f"Já existe: "
                f"{oferta['titulo']}"
            )

            continue

        novos.append(
            oferta
        )

        if len(novos) >= MAX_OFERTAS:

            break

    if not novos:

        print(
            "\nNenhum jogo grátis novo."
        )

        return

    novos_posts = []

    for oferta in novos:

        post = criar_post(
            oferta
        )

        novos_posts.append(
            post
        )

        print(
            "\nNOVO JOGO:"
        )

        print(
            post["titulo"]
        )

        print(
            post["link"]
        )

    posts = (
        novos_posts
        + posts
    )

    posts = posts[
        :MAX_POSTS
    ]

    salvar_posts(
        posts
    )

    print(
        f"\n{len(novos_posts)} "
        "jogo(s) adicionado(s) "
        "ao posts.json."
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    main()
