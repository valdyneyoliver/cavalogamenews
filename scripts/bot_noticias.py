import json
import re
import html
import ssl
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET


# =========================================================
# CONFIGURAÇÕES
# =========================================================

POSTS_FILE = "posts.json"

# Quantidade máxima de notícias novas por execução
MAX_NOTICIAS = 10

# Só aceita notícias publicadas nas últimas X horas
HORAS_MAXIMO = 48

# Mantém no máximo esta quantidade de posts no posts.json
MAX_POSTS = 200


# =========================================================
# FONTES RSS DIRETAS
# =========================================================

FONTES = [
    {
        "nome": "Gematsu",
        "url": "https://www.gematsu.com/feed",
        "categoria": "Notícias",
    },
    {
        "nome": "Eurogamer",
        "url": "https://www.eurogamer.net/feed",
        "categoria": "Notícias",
    },
    {
        "nome": "IGN",
        "url": "https://feeds.ign.com/ign/all",
        "categoria": "Notícias",
    },
    {
        "nome": "GameSpot",
        "url": "https://www.gamespot.com/feeds/mashup/",
        "categoria": "Notícias",
    },
    {
        "nome": "PC Gamer",
        "url": "https://www.pcgamer.com/rss/",
        "categoria": "Pc",
    },
    {
        "nome": "Nintendo Life",
        "url": "https://www.nintendolife.com/feeds/latest",
        "categoria": "Nintendo",
    },
    {
        "nome": "PlayStation Blog",
        "url": "https://blog.playstation.com/feed",
        "categoria": "PlayStation",
    },
    {
        "nome": "Rock Paper Shotgun",
        "url": "https://www.rockpapershotgun.com/feed",
        "categoria": "Pc",
    },
]


# =========================================================
# HTTP
# =========================================================

SSL_CONTEXT = ssl.create_default_context()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def baixar(url, timeout=20):
    """Baixa uma URL e retorna (texto, URL final)."""

    try:
        req = Request(url, headers=HEADERS)

        with urlopen(
            req,
            timeout=timeout,
            context=SSL_CONTEXT
        ) as resposta:

            dados = resposta.read()

            charset = (
                resposta.headers.get_content_charset()
                or "utf-8"
            )

            try:
                texto = dados.decode(
                    charset,
                    errors="replace"
                )

            except LookupError:
                texto = dados.decode(
                    "utf-8",
                    errors="replace"
                )

            return texto, resposta.geturl()

    except Exception as erro:

        print(
            f"[ERRO] Não foi possível baixar "
            f"{url}: {erro}"
        )

        return "", url


# =========================================================
# UTILIDADES
# =========================================================

def limpar_html(texto):

    if not texto:
        return ""

    texto = html.unescape(texto)

    texto = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        texto,
        flags=re.I | re.S
    )

    texto = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        texto,
        flags=re.I | re.S
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


def normalizar_url(url):

    if not url:
        return ""

    url = html.unescape(
        str(url)
    ).strip()

    url = url.strip("\"' ")

    return url


def url_valida(url):

    if not url:
        return False

    try:

        p = urlparse(url)

        if p.scheme not in (
            "http",
            "https"
        ):
            return False

        if not p.netloc:
            return False

        # Nunca usar Google News
        if "news.google.com" in p.netloc.lower():
            return False

        return True

    except Exception:

        return False


def slug(texto):

    texto = html.unescape(
        texto or ""
    ).lower()

    tabela = str.maketrans({
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ö": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
        "ñ": "n",
    })

    texto = texto.translate(tabela)

    texto = re.sub(
        r"[^a-z0-9]+",
        "-",
        texto
    )

    texto = re.sub(
        r"-+",
        "-",
        texto
    )

    texto = texto.strip("-")

    return texto[:100] or "noticia"


def data_brasil(dt):

    return dt.strftime(
        "%d/%m/%Y"
    )


def agora_utc():

    return datetime.now(
        timezone.utc
    )


# =========================================================
# DATAS RSS
# =========================================================

def interpretar_data(valor):

    if not valor:
        return None

    valor = valor.strip()

    # RSS / RFC 2822
    try:

        dt = parsedate_to_datetime(
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

    # ISO 8601
    try:

        texto = valor.replace(
            "Z",
            "+00:00"
        )

        dt = datetime.fromisoformat(
            texto
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


# =========================================================
# XML / RSS
# =========================================================

def texto_elemento(elemento):

    if elemento is None:
        return ""

    return "".join(
        elemento.itertext()
    ).strip()


def encontrar_por_tag(
    elemento,
    nomes
):

    if elemento is None:
        return None

    nomes = {
        nome.lower()
        for nome in nomes
    }

    for item in elemento.iter():

        tag = item.tag

        if not isinstance(tag, str):
            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag in nomes:

            return item

    return None


def link_item(item):

    for filho in list(item):

        tag = filho.tag

        if not isinstance(tag, str):
            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag != "link":
            continue

        href = filho.attrib.get(
            "href",
            ""
        ).strip()

        if href:

            return normalizar_url(
                href
            )

        texto = texto_elemento(
            filho
        )

        if texto:

            return normalizar_url(
                texto
            )

    return ""


def data_item(item):

    for nome in (
        "pubdate",
        "published",
        "updated",
        "date",
        "created",
    ):

        elemento = encontrar_por_tag(
            item,
            [nome]
        )

        if elemento is not None:

            valor = texto_elemento(
                elemento
            )

            if valor:

                dt = interpretar_data(
                    valor
                )

                if dt:

                    return dt

    return None


def titulo_item(item):

    elemento = encontrar_por_tag(
        item,
        ["title"]
    )

    if elemento is None:
        return ""

    return limpar_html(
        texto_elemento(elemento)
    )


def descricao_item(item):

    for nome in (
        "description",
        "summary",
        "content",
        "encoded",
    ):

        elemento = encontrar_por_tag(
            item,
            [nome]
        )

        if elemento is not None:

            valor = texto_elemento(
                elemento
            )

            if valor:

                return limpar_html(
                    valor
                )

    return ""


# =========================================================
# IMAGENS
# =========================================================

def imagem_valida(url):

    if not url:
        return False

    url = normalizar_url(url)

    if not url_valida(url):
        return False

    url_lower = url.lower()

    palavras_ruins = (
        "logo",
        "avatar",
        "favicon",
        "sprite",
        "tracking",
        "pixel",
        "emoji",
        "icon",
        "icon-",
        "placeholder",
        "gravatar",
    )

    if any(
        palavra in url_lower
        for palavra in palavras_ruins
    ):
        return False

    if url_lower.startswith(
        "data:"
    ):
        return False

    return True


def escolher_srcset(srcset):

    if not srcset:
        return ""

    candidatos = []

    for parte in srcset.split(","):

        parte = parte.strip()

        if not parte:
            continue

        pedacos = parte.split()

        if not pedacos:
            continue

        url = pedacos[0]
        peso = 0

        if len(pedacos) > 1:

            marcador = pedacos[1].lower()

            match = re.match(
                r"(\d+)w",
                marcador
            )

            if match:

                peso = int(
                    match.group(1)
                )

            match = re.match(
                r"([\d.]+)x",
                marcador
            )

            if match:

                peso = int(
                    float(
                        match.group(1)
                    ) * 1000
                )

        candidatos.append(
            (peso, url)
        )

    candidatos.sort(
        reverse=True
    )

    for _, url in candidatos:

        if imagem_valida(url):

            return url

    return ""


def imagem_de_objeto(
    valor,
    pagina_url
):

    if isinstance(
        valor,
        str
    ):

        url = urljoin(
            pagina_url,
            valor.strip()
        )

        if imagem_valida(url):

            return url

        return ""

    if isinstance(
        valor,
        list
    ):

        for item in valor:

            resultado = imagem_de_objeto(
                item,
                pagina_url
            )

            if resultado:

                return resultado

        return ""

    if isinstance(
        valor,
        dict
    ):

        for chave in (
            "url",
            "contentUrl",
            "contenturl",
            "@id",
        ):

            item = valor.get(
                chave
            )

            if isinstance(
                item,
                str
            ):

                url = urljoin(
                    pagina_url,
                    item.strip()
                )

                if imagem_valida(url):

                    return url

        return ""

    return ""


def extrair_jsonld_imagem(
    pagina_url,
    texto
):

    padrao = re.compile(
        r'<script[^>]+type=["\']'
        r'application/ld\+json["\'][^>]*>'
        r"(.*?)"
        r"</script>",
        flags=re.I | re.S,
    )

    def procurar(obj):

        if isinstance(
            obj,
            dict
        ):

            for chave, valor in obj.items():

                if str(chave).lower() == "image":

                    resultado = imagem_de_objeto(
                        valor,
                        pagina_url
                    )

                    if resultado:

                        return resultado

                resultado = procurar(
                    valor
                )

                if resultado:

                    return resultado

        elif isinstance(
            obj,
            list
        ):

            for item in obj:

                resultado = procurar(
                    item
                )

                if resultado:

                    return resultado

        return ""

    for bloco in padrao.findall(
        texto
    ):

        bloco = html.unescape(
            bloco
        ).strip()

        try:

            dados = json.loads(
                bloco
            )

        except Exception:

            continue

        resultado = procurar(
            dados
        )

        if resultado:

            return resultado

    return ""


def extrair_imagem_meta(
    pagina_url,
    texto
):

    padroes = [

        r'<meta[^>]+(?:property|name)=["\']'
        r'og:image["\'][^>]+content=["\']'
        r'([^"\']+)',

        r'<meta[^>]+content=["\']'
        r'([^"\']+)["\'][^>]+'
        r'(?:property|name)=["\']og:image["\']',

        r'<meta[^>]+(?:property|name)=["\']'
        r'og:image:url["\'][^>]+content=["\']'
        r'([^"\']+)',

        r'<meta[^>]+content=["\']'
        r'([^"\']+)["\'][^>]+'
        r'(?:property|name)=["\']og:image:url["\']',

        r'<meta[^>]+(?:property|name)=["\']'
        r'twitter:image["\'][^>]+content=["\']'
        r'([^"\']+)',

        r'<meta[^>]+content=["\']'
        r'([^"\']+)["\'][^>]+'
        r'(?:property|name)=["\']twitter:image["\']',

        r'<meta[^>]+(?:property|name)=["\']'
        r'twitter:image:src["\'][^>]+content=["\']'
        r'([^"\']+)',

        r'<meta[^>]+content=["\']'
        r'([^"\']+)["\'][^>]+'
        r'(?:property|name)=["\']twitter:image:src["\']',

        r'<link[^>]+rel=["\']image_src["\']'
        r'[^>]+href=["\']([^"\']+)',

        r'<link[^>]+href=["\']([^"\']+)["\']'
        r'[^>]+rel=["\']image_src["\']',
    ]

    for padrao in padroes:

        encontrados = re.findall(
            padrao,
            texto,
            flags=re.I
        )

        for url in encontrados:

            url = urljoin(
                pagina_url,
                html.unescape(
                    url
                ).strip()
            )

            if imagem_valida(url):

                return url

    return ""


def imagem_da_primeira_tag_img(
    pagina_url,
    texto
):

    padrao = re.compile(
        r"<img\b([^>]+)>",
        flags=re.I | re.S
    )

    atributos = (
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-image",
        "data-lazy",
        "data-url",
        "srcset",
        "data-srcset",
    )

    for bloco in padrao.findall(
        texto
    ):

        attrs = {}

        for nome, valor in re.findall(
            r'([a-zA-Z0-9_:-]+)\s*=\s*'
            r'["\']([^"\']*)["\']',
            bloco,
            flags=re.I,
        ):

            attrs[
                nome.lower()
            ] = html.unescape(
                valor
            ).strip()

        # Primeiro tenta srcset
        for nome in (
            "srcset",
            "data-srcset"
        ):

            valor = attrs.get(
                nome,
                ""
            )

            if valor:

                url = escolher_srcset(
                    valor
                )

                if url:

                    return urljoin(
                        pagina_url,
                        url
                    )

        for nome in atributos:

            if nome.endswith(
                "srcset"
            ):
                continue

            valor = attrs.get(
                nome,
                ""
            )

            if not valor:
                continue

            url = urljoin(
                pagina_url,
                valor
            )

            if imagem_valida(url):

                return url

    return ""


def extrair_imagem_pagina(
    pagina_url
):

    """
    Abre a página ORIGINAL da notícia
    e tenta encontrar a imagem principal.

    Ordem:
    1. JSON-LD
    2. Open Graph
    3. Twitter Card
    4. primeira imagem válida
    """

    texto, url_final = baixar(
        pagina_url
    )

    if not texto:

        return ""

    # 1. JSON-LD
    imagem = extrair_jsonld_imagem(
        url_final,
        texto
    )

    if imagem:

        return imagem

    # 2. Meta tags
    imagem = extrair_imagem_meta(
        url_final,
        texto
    )

    if imagem:

        return imagem

    # 3. <img>
    imagem = imagem_da_primeira_tag_img(
        url_final,
        texto
    )

    if imagem:

        return imagem

    return ""


def extrair_imagem_rss(
    item,
    base_url
):

    # media:content / media:thumbnail
    for elemento in item.iter():

        tag = elemento.tag

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
            "thumbnail"
        ):

            url = elemento.attrib.get(
                "url",
                ""
            ).strip()

            if url:

                url = urljoin(
                    base_url,
                    html.unescape(url)
                )

                if imagem_valida(url):

                    return url

    # enclosure
    for elemento in item.iter():

        tag = elemento.tag

        if not isinstance(
            tag,
            str
        ):
            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag == "enclosure":

            url = elemento.attrib.get(
                "url",
                ""
            ).strip()

            tipo = elemento.attrib.get(
                "type",
                ""
            ).lower()

            if url and (
                "image" in tipo
                or not tipo
            ):

                url = urljoin(
                    base_url,
                    html.unescape(url)
                )

                if imagem_valida(url):

                    return url

    # Imagem dentro da descrição
    descricao_raw = ""

    for nome in (
        "description",
        "summary",
        "content",
        "encoded",
    ):

        elemento = encontrar_por_tag(
            item,
            [nome]
        )

        if elemento is not None:

            descricao_raw = texto_elemento(
                elemento
            )

            if descricao_raw:

                break

    if descricao_raw:

        match = re.search(
            r'<img[^>]+'
            r'(?:src|data-src|data-lazy-src)'
            r'=["\']([^"\']+)',
            descricao_raw,
            flags=re.I
        )

        if match:

            url = urljoin(
                base_url,
                html.unescape(
                    match.group(1)
                ).strip()
            )

            if imagem_valida(url):

                return url

    return ""


# =========================================================
# CATEGORIA
# =========================================================

def descobrir_categoria(
    titulo,
    resumo,
    categoria_padrao
):

    texto = (
        f"{titulo} {resumo}"
    ).lower()

    if any(
        palavra in texto
        for palavra in (
            "playstation",
            "ps5",
            "ps4",
            "ps vr",
            "sony",
        )
    ):

        return "PlayStation"

    if any(
        palavra in texto
        for palavra in (
            "xbox",
            "series x",
            "series s",
            "game pass",
            "microsoft",
        )
    ):

        return "Xbox"

    if any(
        palavra in texto
        for palavra in (
            "nintendo",
            "switch",
            "switch 2",
            "zelda",
            "mario",
            "pokemon",
        )
    ):

        return "Nintendo"

    if any(
        palavra in texto
        for palavra in (
            "pc",
            "steam",
            "epic games",
            "windows",
            "gpu",
            "nvidia",
            "amd",
        )
    ):

        return "Pc"

    return (
        categoria_padrao
        or "Notícias"
    )


# =========================================================
# BUSCAR RSS
# =========================================================

def buscar_rss(fonte):

    nome = fonte["nome"]
    url = fonte["url"]

    categoria = fonte.get(
        "categoria",
        "Notícias"
    )

    print(
        f"\n[RSS] Lendo {nome}: {url}"
    )

    texto, url_final = baixar(
        url
    )

    if not texto:

        return []

    try:

        raiz = ET.fromstring(
            texto
        )

    except Exception as erro:

        print(
            f"[ERRO] RSS inválido "
            f"em {nome}: {erro}"
        )

        return []

    itens = []

    for elemento in raiz.iter():

        tag = elemento.tag

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

        titulo = titulo_item(
            elemento
        )

        link = link_item(
            elemento
        )

        resumo = descricao_item(
            elemento
        )

        data_publicacao = data_item(
            elemento
        )

        if not titulo or not link:

            continue

        link = normalizar_url(
            link
        )

        # Nunca aceitar Google News
        if (
            "news.google.com"
            in urlparse(link).netloc.lower()
        ):

            continue

        if not url_valida(link):

            continue

        if data_publicacao is None:

            data_publicacao = agora_utc()

        idade = (
            agora_utc()
            - data_publicacao
        )

        if idade > timedelta(
            hours=HORAS_MAXIMO
        ):

            continue

        if idade < timedelta(
            minutes=-10
        ):

            continue

        imagem = extrair_imagem_rss(
            elemento,
            url_final
        )

        itens.append({
            "titulo": titulo,
            "link": link,
            "resumo_rss": resumo,
            "data_publicacao": data_publicacao,
            "imagem": imagem,
            "fonte": nome,
            "categoria": categoria,
        })

    print(
        f"[RSS] {nome}: "
        f"{len(itens)} notícia(s) "
        f"recente(s) encontrada(s)."
    )

    return itens


# =========================================================
# RESUMO / CONTEÚDO
# =========================================================

def criar_resumo(
    titulo,
    resumo_rss,
    fonte
):

    resumo = limpar_html(
        resumo_rss
    )

    if not resumo:

        resumo = (
            f"{titulo} — confira "
            "os principais detalhes "
            "desta novidade."
        )

    resumo = re.sub(
        r"\s+",
        " ",
        resumo
    ).strip()

    if len(resumo) > 300:

        resumo = (
            resumo[:297]
            .rsplit(" ", 1)[0]
            + "..."
        )

    # Evita atribuição ao Google News
    resumo = resumo.replace(
        "Google News",
        ""
    )

    resumo = re.sub(
        r"\s+",
        " ",
        resumo
    ).strip()

    if not resumo:

        resumo = (
            f"{titulo} — confira "
            "os principais detalhes "
            "desta novidade."
        )

    return resumo


def criar_conteudo(
    titulo,
    resumo,
    fonte,
    link
):

    return [

        (
            f"{titulo} ganhou destaque "
            "entre as novidades recentes "
            "do mundo dos videogames."
        ),

        resumo,

        (
            f"A informação foi publicada "
            f"originalmente por {fonte}. "
            "O CavaloGameNews reúne os "
            "principais detalhes disponíveis "
            "sobre o assunto."
        ),

        f"🔗 Fonte: {link}",
    ]


# =========================================================
# DEDUPLICAÇÃO
# =========================================================

def normalizar_titulo_para_comparacao(
    titulo
):

    return slug(
        titulo
    )


def coletar_chaves_existentes(
    posts
):

    ids = set()
    links = set()
    titulos = set()

    for post in posts:

        if not isinstance(
            post,
            dict
        ):

            continue

        post_id = str(
            post.get(
                "id",
                ""
            )
        ).strip()

        if post_id:

            ids.add(
                post_id
            )

        link = normalizar_url(
            post.get(
                "link",
                ""
            )
        )

        if link:

            links.add(
                link.rstrip("/")
            )

        titulo = (
            normalizar_titulo_para_comparacao(
                str(
                    post.get(
                        "titulo",
                        ""
                    )
                )
            )
        )

        if titulo:

            titulos.add(
                titulo
            )

    return (
        ids,
        links,
        titulos
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
                "O arquivo posts.json "
                "precisa conter uma lista "
                "de notícias."
            )

        return posts

    except FileNotFoundError:

        print(
            f"[AVISO] {POSTS_FILE} "
            "não encontrado. "
            "Criando lista vazia."
        )

        return []

    except json.JSONDecodeError as erro:

        raise ValueError(
            f"O arquivo {POSTS_FILE} "
            f"contém JSON inválido: {erro}"
        )


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
# CRIAR POST
# =========================================================

def criar_post(noticia):

    titulo = noticia[
        "titulo"
    ].strip()

    link = noticia[
        "link"
    ].strip()

    fonte = noticia[
        "fonte"
    ]

    data_publicacao = (
        noticia.get(
            "data_publicacao"
        )
        or agora_utc()
    )

    data_id = (
        data_publicacao.strftime(
            "%Y%m%d"
        )
    )

    data_str = data_brasil(
        data_publicacao
    )

    resumo = criar_resumo(
        titulo,
        noticia.get(
            "resumo_rss",
            ""
        ),
        fonte
    )

    categoria = descobrir_categoria(
        titulo,
        resumo,
        noticia.get(
            "categoria",
            "Notícias"
        )
    )

    imagem = noticia.get(
        "imagem",
        ""
    )

    # Se o RSS não trouxe imagem,
    # procura na página original.
    if not imagem:

        print(
            "[IMAGEM] Procurando "
            f"imagem original: {titulo}"
        )

        imagem = extrair_imagem_pagina(
            link
        )

    if imagem:

        print(
            f"[IMAGEM] Encontrada: "
            f"{imagem}"
        )

    else:

        print(
            "[IMAGEM] Nenhuma imagem "
            "encontrada."
        )

    post_id = (
        f"{data_id}-{slug(titulo)}"
    )

    return {

        "id": post_id,

        "titulo": titulo,

        "categoria": categoria,

        "data": data_str,

        "imagem": imagem,

        "resumo": resumo,

        "link": link,

        "x": "",

        "videos": [
            {
                "tipo": "youtube",
                "url": "xxx"
            }
        ],

        "conteudo": criar_conteudo(
            titulo,
            resumo,
            fonte,
            link
        )
    }


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)

    print(
        "CavaloGameNews - "
        "Bot automático de notícias"
    )

    print("=" * 60)

    posts = carregar_posts()

    (
        ids_existentes,
        links_existentes,
        titulos_existentes
    ) = coletar_chaves_existentes(
        posts
    )

    noticias = []

    # -----------------------------------------------------
    # LER TODAS AS FONTES
    # -----------------------------------------------------

    for fonte in FONTES:

        try:

            resultados = buscar_rss(
                fonte
            )

            noticias.extend(
                resultados
            )

        except Exception as erro:

            print(
                f"[ERRO] Falha ao "
                f"processar {fonte['nome']}: "
                f"{erro}"
            )

    # -----------------------------------------------------
    # ORDENAR DA MAIS NOVA PARA A MAIS ANTIGA
    # -----------------------------------------------------

    noticias.sort(
        key=lambda item: item.get(
            "data_publicacao",
            datetime.min.replace(
                tzinfo=timezone.utc
            )
        ),
        reverse=True
    )

    novas = []

    # -----------------------------------------------------
    # CRIAR NOTÍCIAS NOVAS
    # -----------------------------------------------------

    for noticia in noticias:

        if len(novas) >= MAX_NOTICIAS:

            break

        link = normalizar_url(
            noticia.get(
                "link",
                ""
            )
        )

        titulo = noticia.get(
            "titulo",
            ""
        ).strip()

        chave_titulo = (
            normalizar_titulo_para_comparacao(
                titulo
            )
        )

        # Já existe pelo link
        if (
            link
            and link.rstrip("/")
            in links_existentes
        ):

            continue

        # Já existe pelo título
        if (
            chave_titulo
            and chave_titulo
            in titulos_existentes
        ):

            continue

        post = criar_post(
            noticia
        )

        if post[
            "id"
        ] in ids_existentes:

            continue

        novas.append(
            post
        )

        ids_existentes.add(
            post["id"]
        )

        if link:

            links_existentes.add(
                link.rstrip("/")
            )

        if chave_titulo:

            titulos_existentes.add(
                chave_titulo
            )

        print(
            f"[NOVA] {post['titulo']}"
        )

    # -----------------------------------------------------
    # NENHUMA NOTÍCIA NOVA
    # -----------------------------------------------------

    if not novas:

        print(
            "\nNenhuma notícia "
            "nova encontrada."
        )

        return

    # -----------------------------------------------------
    # NOVAS NOTÍCIAS NO COMEÇO
    # -----------------------------------------------------

    posts = novas + posts

    # Limite de segurança
    posts = posts[:MAX_POSTS]

    # Salvar
    salvar_posts(
        posts
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        f"{len(novas)} notícia(s) "
        "adicionada(s)."
    )

    print(
        f"{len(posts)} notícia(s) "
        f"atualmente em {POSTS_FILE}."
    )

    print(
        "=" * 60
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    main()
