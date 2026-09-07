import json
import re
import html
from datetime import datetime
from urllib.request import Request, urlopen


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = "posts.json"

MAX_OFERTAS_POR_LOJA = 10
MAX_POSTS = 200

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}


# =========================================================
# API DA EPIC GAMES
# =========================================================

EPIC_API = (
    "https://store-site-backend-static.ak.epicgames.com/"
    "freeGamesPromotions"
    "?locale=pt-BR"
    "&country=BR"
    "&allowCountries=BR"
)


# =========================================================
# API DA GOG
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


# =========================================================
# BAIXAR JSON
# =========================================================

def baixar_json(url):

    try:

        req = Request(
            url,
            headers=HEADERS
        )

        with urlopen(req, timeout=30) as resposta:

            conteudo = resposta.read().decode(
                "utf-8"
            )

        return json.loads(conteudo)

    except Exception as erro:

        print(
            f"Erro ao acessar API: {erro}"
        )

        return None


# =========================================================
# LIMPAR HTML
# =========================================================

def limpar_html(texto):

    if not texto:
        return ""

    texto = html.unescape(
        str(texto)
    )

    texto = re.sub(
        r"<[^>]+>",
        "",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# =========================================================
# CRIAR ID
# =========================================================

def criar_id(titulo):

    texto = titulo.lower()

    texto = re.sub(
        r"[^a-z0-9áéíóúãõâêôç]+",
        "-",
        texto
    )

    texto = texto.strip("-")

    data = datetime.now().strftime(
        "%Y%m%d"
    )

    return f"{data}-{texto}"


# =========================================================
# =========================================================
# EPIC GAMES
# =========================================================
# =========================================================


# =========================================================
# ENCONTRAR IMAGEM DA EPIC
# =========================================================

def encontrar_imagem_epic(item):

    imagens = item.get(
        "keyImages",
        []
    )

    if not isinstance(
        imagens,
        list
    ):
        return ""

    # Primeiro tenta imagens maiores
    for imagem in imagens:

        url = imagem.get(
            "url",
            ""
        )

        if not url:
            continue

        tipo = imagem.get(
            "type",
            ""
        ).lower()

        if (
            "thumbnail" not in tipo
            and "logo" not in tipo
        ):

            return url

    # Segunda tentativa
    for imagem in imagens:

        url = imagem.get(
            "url",
            ""
        )

        if url:
            return url

    return ""


# =========================================================
# ENCONTRAR LINK DIRETO DA EPIC
# =========================================================

def encontrar_link_epic(item):

    # -----------------------------------------------------
    # 1. Campos que podem possuir URL direta
    # -----------------------------------------------------

    campos = [
        "url",
        "storeUrl",
        "productUrl",
        "pageUrl",
        "link",
    ]

    for campo in campos:

        valor = item.get(
            campo,
            ""
        )

        if (
            isinstance(valor, str)
            and valor.startswith("http")
            and "epicgames.com" in valor
        ):

            return valor

    # -----------------------------------------------------
    # 2. catalogNs / mappings
    # -----------------------------------------------------

    catalog_ns = item.get(
        "catalogNs",
        {}
    )

    mappings = catalog_ns.get(
        "mappings",
        []
    )

    if isinstance(
        mappings,
        list
    ):

        for mapping in mappings:

            if not isinstance(
                mapping,
                dict
            ):
                continue

            slug = (
                mapping.get("pageSlug")
                or mapping.get("slug")
                or ""
            )

            if slug:

                return (
                    "https://store.epicgames.com/"
                    f"p/{slug}"
                )

    # -----------------------------------------------------
    # 3. productSlug
    # -----------------------------------------------------

    slug = item.get(
        "productSlug",
        ""
    )

    if slug:

        return (
            "https://store.epicgames.com/"
            f"p/{slug}"
        )

    # -----------------------------------------------------
    # 4. urlSlug
    # -----------------------------------------------------

    slug = item.get(
        "urlSlug",
        ""
    )

    if slug:

        return (
            "https://store.epicgames.com/"
            f"p/{slug}"
        )

    return ""


# =========================================================
# VERIFICAR SE EPIC ESTÁ GRÁTIS
# =========================================================

def epic_esta_gratis(item):

    promotions = item.get(
        "promotions"
    ) or {}

    grupos = promotions.get(
        "promotionalOffers",
        []
    )

    if isinstance(
        grupos,
        list
    ):

        for grupo in grupos:

            if not isinstance(
                grupo,
                dict
            ):
                continue

            ofertas = grupo.get(
                "promotionalOffers",
                []
            )

            if not isinstance(
                ofertas,
                list
            ):
                continue

            for oferta in ofertas:

                if not isinstance(
                    oferta,
                    dict
                ):
                    continue

                desconto = (
                    oferta
                    .get(
                        "discountSetting",
                        {}
                    )
                    .get(
                        "discountPercentage"
                    )
                )

                if desconto == 0:

                    return True

    # -----------------------------------------------------
    # Verificação pelo preço
    # -----------------------------------------------------

    preco = (
        item
        .get(
            "price",
            {}
        )
        .get(
            "totalPrice",
            {}
        )
    )

    if isinstance(
        preco,
        dict
    ):

        preco_final = preco.get(
            "discountPrice"
        )

        if preco_final == 0:

            return True

    return False


# =========================================================
# BUSCAR JOGOS GRÁTIS DA EPIC
# =========================================================

def buscar_epic():

    print()
    print("=" * 60)
    print("CONSULTANDO EPIC GAMES")
    print("=" * 60)

    dados = baixar_json(
        EPIC_API
    )

    if not dados:

        print(
            "Não foi possível acessar a Epic Games."
        )

        return []

    try:

        elementos = (
            dados
            .get("data", {})
            .get("Catalog", {})
            .get("searchStore", {})
            .get("elements", [])
        )

    except Exception:

        elementos = []

    print(
        f"Epic encontrou "
        f"{len(elementos)} produto(s) para analisar."
    )

    encontrados = []

    for item in elementos:

        try:

            if not isinstance(
                item,
                dict
            ):
                continue

            # -------------------------------------------------
            # TÍTULO
            # -------------------------------------------------

            titulo = limpar_html(
                item.get("title")
                or item.get("productName")
                or ""
            )

            if not titulo:
                continue

            # -------------------------------------------------
            # VERIFICAR GRATUITO
            # -------------------------------------------------

            if not epic_esta_gratis(
                item
            ):
                continue

            # -------------------------------------------------
            # LINK
            # -------------------------------------------------

            link = encontrar_link_epic(
                item
            )

            if not link:

                print(
                    f"Link não encontrado: {titulo}"
                )

                continue

            # -------------------------------------------------
            # IMAGEM
            # -------------------------------------------------

            imagem = encontrar_imagem_epic(
                item
            )

            # -------------------------------------------------
            # RESUMO
            # -------------------------------------------------

            resumo = (
                f"{titulo} está disponível "
                "gratuitamente por tempo limitado "
                "na Epic Games."
            )

            # -------------------------------------------------
            # CONTEÚDO
            # -------------------------------------------------

            conteudo = [

                (
                    f"O jogo {titulo} está disponível "
                    "gratuitamente na Epic Games."
                ),

                (
                    f"{titulo} pode ser resgatado "
                    "gratuitamente durante o período "
                    "da promoção."
                ),

                (
                    "Depois de resgatar o jogo, ele ficará "
                    "vinculado à sua conta da Epic Games."
                ),

                (
                    "A promoção é por tempo limitado, "
                    "então é recomendado resgatar o jogo "
                    "enquanto ele estiver disponível."
                ),

                (
                    f"Para resgatar {titulo}, acesse: {link}"
                ),

            ]

            encontrados.append({

                "titulo": titulo,

                "imagem": imagem,

                "resumo": resumo,

                "link": link,

                "loja": "Epic Games",

                "conteudo": conteudo,

            })

            print(
                f"Epic Games: {titulo}"
            )

            print(
                f"Link: {link}"
            )

            if (
                len(encontrados)
                >= MAX_OFERTAS_POR_LOJA
            ):
                break

        except Exception as erro:

            print(
                f"Erro ao processar Epic: {erro}"
            )

    print(
        f"Epic Games encontrou "
        f"{len(encontrados)} jogo(s) grátis."
    )

    return encontrados


# =========================================================
# =========================================================
# GOG
# =========================================================
# =========================================================


# =========================================================
# ENCONTRAR IMAGEM DA GOG
# =========================================================

def encontrar_imagem_gog(item):

    # -----------------------------------------------------
    # Campos diretos
    # -----------------------------------------------------

    campos = [
        "image",
        "coverHorizontal",
        "coverVertical",
        "backgroundImage",
    ]

    for campo in campos:

        valor = item.get(
            campo,
            ""
        )

        if (
            isinstance(valor, str)
            and valor.startswith("http")
        ):

            return valor

    # -----------------------------------------------------
    # Campo images
    # -----------------------------------------------------

    imagens = item.get(
        "images",
        {}
    )

    if isinstance(
        imagens,
        dict
    ):

        for valor in imagens.values():

            if (
                isinstance(valor, str)
                and valor.startswith("http")
            ):

                return valor

    return ""


# =========================================================
# ENCONTRAR LINK DA GOG
# =========================================================

def encontrar_link_gog(item):

    # -----------------------------------------------------
    # Campos que podem ter URL
    # -----------------------------------------------------

    campos = [
        "url",
        "productUrl",
        "link",
    ]

    for campo in campos:

        valor = item.get(
            campo,
            ""
        )

        if (
            isinstance(valor, str)
            and "gog.com" in valor
        ):

            return valor

    # -----------------------------------------------------
    # Slug
    # -----------------------------------------------------

    slug = (
        item.get("slug")
        or item.get("productSlug")
        or ""
    )

    if slug:

        return (
            "https://www.gog.com/en/game/"
            f"{slug}"
        )

    return ""


# =========================================================
# BUSCAR JOGOS GRÁTIS DA GOG
# =========================================================

def buscar_gog():

    print()
    print("=" * 60)
    print("CONSULTANDO GOG")
    print("=" * 60)

    dados = baixar_json(
        GOG_API
    )

    if not dados:

        print(
            "Não foi possível acessar a GOG."
        )

        return []

    produtos = (
        dados.get("products")
        or dados.get("items")
        or dados.get("results")
        or []
    )

    if not isinstance(
        produtos,
        list
    ):

        print(
            "Formato da resposta da GOG "
            "não reconhecido."
        )

        return []

    print(
        f"GOG encontrou "
        f"{len(produtos)} produto(s) para analisar."
    )

    encontrados = []

    for item in produtos:

        try:

            if not isinstance(
                item,
                dict
            ):
                continue

            # -------------------------------------------------
            # TÍTULO
            # -------------------------------------------------

            titulo = limpar_html(
                item.get("title")
                or item.get("name")
                or ""
            )

            if not titulo:
                continue

            # -------------------------------------------------
            # LINK
            # -------------------------------------------------

            link = encontrar_link_gog(
                item
            )

            if not link:
                continue

            # -------------------------------------------------
            # IMAGEM
            # -------------------------------------------------

            imagem = encontrar_imagem_gog(
                item
            )

            # -------------------------------------------------
            # RESUMO
            # -------------------------------------------------

            resumo = (
                f"{titulo} está disponível "
                "gratuitamente na GOG."
            )

            # -------------------------------------------------
            # CONTEÚDO
            # -------------------------------------------------

            conteudo = [

                (
                    f"O jogo {titulo} está disponível "
                    "gratuitamente na GOG."
                ),

                (
                    "A GOG disponibiliza o jogo "
                    "gratuitamente durante a promoção."
                ),

                (
                    "Depois de resgatar o jogo, "
                    "ele ficará vinculado à sua conta "
                    "da GOG."
                ),

                (
                    "A oferta pode mudar com o tempo, "
                    "por isso é recomendado conferir "
                    "a página oficial."
                ),

                (
                    f"Para conferir {titulo}, "
                    f"acesse: {link}"
                ),

            ]

            encontrados.append({

                "titulo": titulo,

                "imagem": imagem,

                "resumo": resumo,

                "link": link,

                "loja": "GOG",

                "conteudo": conteudo,

            })

            print(
                f"GOG: {titulo}"
            )

            print(
                f"Link: {link}"
            )

            if (
                len(encontrados)
                >= MAX_OFERTAS_POR_LOJA
            ):
                break

        except Exception as erro:

            print(
                f"Erro ao processar GOG: {erro}"
            )

    print(
        f"GOG encontrou "
        f"{len(encontrados)} jogo(s) grátis."
    )

    return encontrados


# =========================================================
# =========================================================
# POSTS
# =========================================================
# =========================================================


# =========================================================
# CARREGAR POSTS
# =========================================================

def carregar_posts():

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

        arquivo.write("\n")


# =========================================================
# VERIFICAR DUPLICADO
# =========================================================

def ja_existe(posts, titulo):

    titulo_normalizado = (
        titulo
        .lower()
        .strip()
    )

    finais = [

        " está grátis por tempo limitado",

        " está disponível gratuitamente",

        " está grátis na gog",

        " está grátis na steam",

    ]

    for post in posts:

        titulo_post = (
            str(
                post.get(
                    "titulo",
                    ""
                )
            )
            .lower()
            .strip()
        )

        for final in finais:

            titulo_post = titulo_post.replace(
                final,
                ""
            )

        if (
            titulo_post
            == titulo_normalizado
        ):

            return True

    return False


# =========================================================
# ADICIONAR NOTÍCIAS
# =========================================================

def adicionar_noticias():

    posts = carregar_posts()

    ids_existentes = {

        str(
            post.get(
                "id",
                ""
            )
        )

        for post in posts

    }

    # -----------------------------------------------------
    # BUSCAR EPIC
    # -----------------------------------------------------

    epic = buscar_epic()

    # -----------------------------------------------------
    # BUSCAR GOG
    # -----------------------------------------------------

    gog = buscar_gog()

    # -----------------------------------------------------
    # JUNTAR RESULTADOS
    # -----------------------------------------------------

    ofertas = []

    ofertas.extend(
        epic
    )

    ofertas.extend(
        gog
    )

    # -----------------------------------------------------
    # NENHUMA OFERTA
    # -----------------------------------------------------

    if not ofertas:

        print()
        print(
            "Nenhum jogo grátis encontrado."
        )

        return

    print()
    print(
        f"Total encontrado: {len(ofertas)}"
    )

    novas = []

    data_atual = datetime.now().strftime(
        "%d/%m/%Y"
    )

    # -----------------------------------------------------
    # PROCESSAR OFERTAS
    # -----------------------------------------------------

    for oferta in ofertas:

        titulo = oferta["titulo"]

        loja = oferta["loja"]

        # -------------------------------------------------
        # CRIAR ID
        # -------------------------------------------------

        post_id = criar_id(
            f"{titulo}-{loja}"
        )

        # -------------------------------------------------
        # DUPLICADO POR ID
        # -------------------------------------------------

        if post_id in ids_existentes:

            print(
                f"Já existe: "
                f"{titulo} ({loja})"
            )

            continue

        # -------------------------------------------------
        # DUPLICADO POR TÍTULO
        # -------------------------------------------------

        if ja_existe(
            posts,
            titulo
        ):

            print(
                f"Já existe: "
                f"{titulo} ({loja})"
            )

            continue

        # -------------------------------------------------
        # TÍTULO DA NOTÍCIA
        # -------------------------------------------------

        if loja == "Epic Games":

            titulo_final = (
                f"{titulo} está grátis por tempo limitado"
            )

        else:

            titulo_final = (
                f"{titulo} está grátis na GOG"
            )

        # -------------------------------------------------
        # CRIAR POST
        # -------------------------------------------------

        post = {

            "id": post_id,

            "titulo": titulo_final,

            "categoria": "Jogos Grátis",

            "data": data_atual,

            "imagem": oferta["imagem"],

            "resumo": oferta["resumo"],

            "x": "",

            "videos": [],

            "conteudo": oferta["conteudo"],

        }

        novas.append(
            post
        )

        print()
        print(
            f"Nova notícia adicionada: "
            f"{titulo_final}"
        )

    # -----------------------------------------------------
    # NENHUMA NOTÍCIA NOVA
    # -----------------------------------------------------

    if not novas:

        print()
        print(
            "Nenhuma notícia nova para adicionar."
        )

        return

    # -----------------------------------------------------
    # COLOCAR NOVAS PRIMEIRO
    # -----------------------------------------------------

    posts = novas + posts

    # -----------------------------------------------------
    # LIMITAR POSTS
    # -----------------------------------------------------

    posts = posts[:MAX_POSTS]

    # -----------------------------------------------------
    # SALVAR
    # -----------------------------------------------------

    salvar_posts(
        posts
    )

    print()
    print(
        f"{len(novas)} nova(s) "
        "notícia(s) adicionada(s)."
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "BOT DE JOGOS GRÁTIS"
    )

    print(
        "CAVALOGAMENEWS"
    )

    print(
        "EPIC GAMES + GOG"
    )

    print("=" * 60)

    adicionar_noticias()

    print("=" * 60)

    print(
        "Bot finalizado."
    )

    print("=" * 60)
