import json
import re
import html
from datetime import datetime
from urllib.request import Request, urlopen


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = "posts.json"

MAX_OFERTAS = 10
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

        print(f"Erro ao acessar API: {erro}")

        return None


# =========================================================
# LIMPAR TEXTO
# =========================================================

def limpar_html(texto):

    if not texto:
        return ""

    texto = html.unescape(texto)

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
# ENCONTRAR IMAGEM
# =========================================================

def encontrar_imagem(item):

    imagens = item.get(
        "keyImages",
        []
    )

    if not isinstance(imagens, list):
        return ""

    # Tenta primeiro imagens maiores
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

    # Se não encontrar, usa qualquer imagem
    for imagem in imagens:

        url = imagem.get(
            "url",
            ""
        )

        if url:
            return url

    return ""


# =========================================================
# ENCONTRAR URL DIRETA DO JOGO
# =========================================================

def encontrar_link(item):

    # -----------------------------------------------------
    # 1. Tenta campos que podem conter a URL diretamente
    # -----------------------------------------------------

    possiveis_campos = [
        "url",
        "storeUrl",
        "productUrl",
        "pageUrl",
        "link",
    ]

    for campo in possiveis_campos:

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
    # 2. Verifica mappings
    # -----------------------------------------------------

    catalog_ns = item.get(
        "catalogNs",
        {}
    )

    mappings = catalog_ns.get(
        "mappings",
        []
    )

    if isinstance(mappings, list):

        for mapping in mappings:

            if not isinstance(mapping, dict):
                continue

            # Alguns produtos possuem pageSlug
            page_slug = mapping.get(
                "pageSlug"
            )

            if page_slug:

                return (
                    "https://store.epicgames.com/"
                    f"p/{page_slug}"
                )

            # Outros podem possuir pageType
            page_type = mapping.get(
                "pageType"
            )

            if page_type:

                page_slug = mapping.get(
                    "pageSlug",
                    ""
                )

                if page_slug:

                    return (
                        "https://store.epicgames.com/"
                        f"p/{page_slug}"
                    )

    # -----------------------------------------------------
    # 3. Tenta productSlug
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
    # 4. Tenta urlSlug
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

    # -----------------------------------------------------
    # 5. Última tentativa: catalogNs
    # -----------------------------------------------------

    mappings = (
        item
        .get("catalogNs", {})
        .get("mappings", [])
    )

    if isinstance(mappings, list):

        for mapping in mappings:

            if not isinstance(mapping, dict):
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

    return ""


# =========================================================
# VERIFICAR SE ESTÁ GRÁTIS
# =========================================================

def jogo_esta_gratis(item):

    # -----------------------------------------------------
    # Promoções
    # -----------------------------------------------------

    promotions = item.get(
        "promotions"
    ) or {}

    grupos = promotions.get(
        "promotionalOffers",
        []
    )

    if isinstance(grupos, list):

        for grupo in grupos:

            if not isinstance(grupo, dict):
                continue

            ofertas = grupo.get(
                "promotionalOffers",
                []
            )

            if not isinstance(ofertas, list):
                continue

            for oferta in ofertas:

                if not isinstance(oferta, dict):
                    continue

                desconto = (
                    oferta
                    .get("discountSetting", {})
                    .get("discountPercentage")
                )

                if desconto == 0:

                    return True

    # -----------------------------------------------------
    # Preço
    # -----------------------------------------------------

    preco = (
        item
        .get("price", {})
        .get("totalPrice", {})
    )

    if isinstance(preco, dict):

        preco_final = preco.get(
            "discountPrice"
        )

        if preco_final == 0:

            return True

    return False


# =========================================================
# BUSCAR EPIC GAMES
# =========================================================

def buscar_epic():

    print(
        "Consultando Epic Games..."
    )

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
        f"Epic encontrou {len(elementos)} produto(s) para analisar."
    )

    encontrados = []

    for item in elementos:

        try:

            if not isinstance(item, dict):
                continue

            # -------------------------------------------------
            # TÍTULO
            # -------------------------------------------------

            titulo = (
                item.get("title")
                or item.get("productName")
                or ""
            )

            titulo = limpar_html(
                titulo
            )

            if not titulo:
                continue

            # -------------------------------------------------
            # VERIFICAR GRATUITO
            # -------------------------------------------------

            if not jogo_esta_gratis(item):
                continue

            # -------------------------------------------------
            # LINK
            # -------------------------------------------------

            link = encontrar_link(
                item
            )

            if not link:

                print(
                    f"Não foi possível encontrar o link de: {titulo}"
                )

                continue

            # -------------------------------------------------
            # IMAGEM
            # -------------------------------------------------

            imagem = encontrar_imagem(
                item
            )

            # -------------------------------------------------
            # RESUMO EM PORTUGUÊS
            # -------------------------------------------------

            resumo = (
                f"{titulo} está disponível gratuitamente "
                "por tempo limitado na Epic Games."
            )

            # -------------------------------------------------
            # CONTEÚDO EM PORTUGUÊS
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

                "link_jogo": link,

                "conteudo": conteudo,

            })

            print(
                f"Jogo grátis encontrado: {titulo}"
            )

            print(
                f"Link: {link}"
            )

            if len(encontrados) >= MAX_OFERTAS:
                break

        except Exception as erro:

            print(
                f"Erro ao processar jogo: {erro}"
            )

    print(
        f"Epic Games: {len(encontrados)} jogo(s) grátis encontrado(s)."
    )

    return encontrados


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

        if isinstance(dados, list):

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
# ADICIONAR NOTÍCIAS
# =========================================================

def adicionar_noticias():

    posts = carregar_posts()

    ids_existentes = {
        str(post.get("id", ""))
        for post in posts
    }

    ofertas = buscar_epic()

    if not ofertas:

        print(
            "Nenhum jogo grátis encontrado."
        )

        return

    novas = []

    data_atual = datetime.now().strftime(
        "%d/%m/%Y"
    )

    for oferta in ofertas:

        titulo = oferta["titulo"]

        post_id = criar_id(
            titulo
        )

        # -------------------------------------------------
        # VERIFICAR DUPLICADO PELO ID
        # -------------------------------------------------

        if post_id in ids_existentes:

            print(
                f"Já existe no site: {titulo}"
            )

            continue

        # -------------------------------------------------
        # VERIFICAR DUPLICADO PELO TÍTULO
        # -------------------------------------------------

        titulo_normalizado = (
            titulo
            .lower()
            .strip()
        )

        existe_titulo = any(

            str(
                post.get(
                    "titulo",
                    ""
                )
            )
            .lower()
            .strip()
            .replace(
                " está grátis por tempo limitado",
                ""
            )
            == titulo_normalizado

            for post in posts

        )

        if existe_titulo:

            print(
                f"Já existe no site: {titulo}"
            )

            continue

        # -------------------------------------------------
        # CRIAR POST
        # -------------------------------------------------

        post = {

            "id": post_id,

            "titulo": (
                f"{titulo} está grátis por tempo limitado"
            ),

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

        print(
            f"Nova notícia adicionada: {titulo}"
        )

    # -----------------------------------------------------
    # SALVAR
    # -----------------------------------------------------

    if not novas:

        print(
            "Nenhuma notícia nova para adicionar."
        )

        return

    posts = novas + posts

    posts = posts[:MAX_POSTS]

    salvar_posts(
        posts
    )

    print(
        f"{len(novas)} nova(s) notícia(s) adicionada(s)."
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "BOT DE JOGOS GRÁTIS - CAVALOGAMENEWS"
    )

    print("=" * 60)

    adicionar_noticias()

    print("=" * 60)

    print(
        "Bot finalizado."
    )

    print("=" * 60)
