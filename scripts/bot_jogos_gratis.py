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
# FUNÇÕES
# =========================================================

def baixar_json(url):
    """Baixa JSON de uma URL."""
    try:
        req = Request(url, headers=HEADERS)

        with urlopen(req, timeout=30) as resposta:
            dados = resposta.read().decode("utf-8")

        return json.loads(dados)

    except Exception as erro:
        print(f"Erro ao acessar API: {erro}")
        return None


def limpar_html(texto):
    """Remove HTML e limpa espaços."""
    if not texto:
        return ""

    texto = html.unescape(texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def criar_id(titulo):
    """Cria um ID simples para a notícia."""

    texto = titulo.lower()

    texto = re.sub(
        r"[^a-z0-9áéíóúãõâêôç]+",
        "-",
        texto
    )

    texto = texto.strip("-")

    data = datetime.now().strftime("%Y%m%d")

    return f"{data}-{texto}"


def encontrar_imagem(item):
    """Procura a melhor imagem disponível."""

    imagens = item.get("keyImages", [])

    if isinstance(imagens, list):

        # Primeiro tenta encontrar uma imagem grande
        for imagem in imagens:

            url = imagem.get("url", "")

            if url:
                tipo = imagem.get("type", "").lower()

                if "thumbnail" not in tipo:
                    return url

        # Se não encontrar, usa a primeira
        for imagem in imagens:

            url = imagem.get("url", "")

            if url:
                return url

    return ""


def encontrar_slug(item):
    """Procura o slug usado no endereço da Epic."""

    slug = (
        item.get("productSlug")
        or item.get("urlSlug")
        or item.get("catalogNs", {})
        .get("mappings", [{}])[0]
        .get("pageSlug", "")
    )

    return slug


# =========================================================
# BUSCAR JOGOS GRÁTIS NA EPIC
# =========================================================

def buscar_epic():

    print("Consultando Epic Games...")

    dados = baixar_json(EPIC_API)

    if not dados:
        print("Não foi possível acessar a Epic Games.")
        return []

    encontrados = []

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

    print(f"Epic encontrou {len(elementos)} produto(s) para analisar.")

    for item in elementos:

        try:

            titulo = (
                item.get("title")
                or item.get("productName")
                or ""
            ).strip()

            if not titulo:
                continue

            # -------------------------------------------------
            # VERIFICAR PROMOÇÃO
            # -------------------------------------------------

            promotions = item.get("promotions") or {}

            ofertas = promotions.get(
                "promotionalOffers",
                []
            )

            esta_gratis = False

            for grupo in ofertas:

                ofertas_grupo = grupo.get(
                    "promotionalOffers",
                    []
                )

                for oferta in ofertas_grupo:

                    desconto = oferta.get(
                        "discountSetting",
                        {}
                    ).get(
                        "discountPercentage"
                    )

                    if desconto == 0:
                        esta_gratis = True
                        break

                if esta_gratis:
                    break

            # -------------------------------------------------
            # VERIFICAR PREÇO
            # -------------------------------------------------

            if not esta_gratis:

                preco = (
                    item.get("price", {})
                    .get("totalPrice", {})
                )

                preco_final = preco.get(
                    "discountPrice"
                )

                if preco_final == 0:
                    esta_gratis = True

            if not esta_gratis:
                continue

            # -------------------------------------------------
            # SLUG
            # -------------------------------------------------

            slug = encontrar_slug(item)

            if not slug:
                print(f"Slug não encontrado: {titulo}")
                continue

            # -------------------------------------------------
            # LINK DIRETO
            # -------------------------------------------------

            link = (
                "https://store.epicgames.com/"
                f"pt-BR/p/{slug}"
            )

            # -------------------------------------------------
            # IMAGEM
            # -------------------------------------------------

            imagem = encontrar_imagem(item)

            # -------------------------------------------------
            # DESCRIÇÃO
            # -------------------------------------------------

            # NÃO usamos a descrição original da Epic.
            # Ela pode estar em inglês.

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
                    f"{titulo} pode ser resgatado gratuitamente "
                    "durante o período da promoção."
                ),

                (
                    "Depois de resgatar o jogo, ele fica "
                    "vinculado à sua conta da Epic Games."
                ),

                (
                    "A promoção é por tempo limitado e pode "
                    "terminar a qualquer momento."
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

            if len(encontrados) >= MAX_OFERTAS:
                break

        except Exception as erro:

            print(
                f"Erro ao processar {item.get('title', 'jogo')}: "
                f"{erro}"
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

            dados = json.load(arquivo)

            if isinstance(dados, list):
                return dados

    except Exception as erro:

        print(f"Erro ao ler posts.json: {erro}")

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

        print("Nenhum jogo grátis novo encontrado.")
        return

    novas = []

    data_atual = datetime.now().strftime("%d/%m/%Y")

    for oferta in ofertas:

        titulo = oferta["titulo"]

        post_id = criar_id(titulo)

        # -------------------------------------------------
        # EVITAR DUPLICADOS
        # -------------------------------------------------

        titulo_normalizado = titulo.lower().strip()

        titulo_existente = any(
            str(post.get("titulo", "")).lower().strip()
            == titulo_normalizado
            for post in posts
        )

        if post_id in ids_existentes or titulo_existente:

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

        novas.append(post)

        print(
            f"Novo jogo grátis adicionado: {titulo}"
        )

    # -----------------------------------------------------
    # SALVAR
    # -----------------------------------------------------

    if not novas:

        print("Nenhuma notícia nova para adicionar.")
        return

    posts = novas + posts

    posts = posts[:MAX_POSTS]

    salvar_posts(posts)

    print(
        f"{len(novas)} nova(s) notícia(s) adicionada(s)."
    )


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("BOT DE JOGOS GRÁTIS - CAVALOGAMENEWS")
    print("=" * 60)

    adicionar_noticias()

    print("=" * 60)
    print("Bot finalizado.")
    print("=" * 60)
