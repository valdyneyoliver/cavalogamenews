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

MAX_NOTICIAS = 10
HORAS_MAXIMO = 48
MAX_POSTS = 200


# =========================================================
# FONTES
# =========================================================
# Fontes brasileiras / em português.
#
# O bot tenta todas as fontes.
# Se uma delas estiver temporariamente indisponível,
# ele continua usando as outras.
# =========================================================

FONTES = [
    {
        "nome": "GameVicio",
        "url": "https://www.gamevicio.com/rss",
        "categoria": "Notícias",
    },
    {
        "nome": "Adrenaline",
        "url": "https://www.adrenaline.com.br/feed",
        "categoria": "Notícias",
    },
    {
        "nome": "Canaltech",
        "url": "https://canaltech.com.br/rss/",
        "categoria": "Notícias",
    },
    {
        "nome": "Drops de Jogos",
        "url": "https://dropsdejogos.uai.com.br/feed/",
        "categoria": "Notícias",
    },
    {
        "nome": "Tecnoblog",
        "url": "https://tecnoblog.net/feed/",
        "categoria": "Notícias",
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
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def baixar(url, timeout=20):
    try:
        req = Request(
            url,
            headers=HEADERS
        )

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

    return html.unescape(
        str(url)
    ).strip().strip("\"'")


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

    return texto.strip("-")[:100] or "noticia"


def agora_utc():
    return datetime.now(
        timezone.utc
    )


def data_brasil(dt):
    return dt.strftime(
        "%d/%m/%Y"
    )


# =========================================================
# DATAS
# =========================================================

def interpretar_data(valor):

    if not valor:
        return None

    valor = valor.strip()

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

    try:
        dt = datetime.fromisoformat(
            valor.replace(
                "Z",
                "+00:00"
            )
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

        if not isinstance(
            tag,
            str
        ):
            continue

        tag = tag.split(
            "}"
        )[-1].lower()

        if tag in nomes:
            return item

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

            texto = texto_elemento(
                elemento
            )

            if texto:
                return limpar_html(
                    texto
                )

    return ""


def link_item(item):

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

            dt = interpretar_data(
                valor
            )

            if dt:
                return dt

    return None
```python
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
        "placeholder",
        "gravatar",
        "icon",
    )

    if any(
        palavra in url_lower
        for palavra in palavras_ruins
    ):
        return False

    if url_lower.startswith("data:"):
        return False

    return True


def escolher_srcset(srcset):

    if not srcset:
        return ""

    candidatos = []

    for parte in srcset.split(","):

        partes = parte.strip().split()

        if not partes:
            continue

        url = partes[0]
        tamanho = 0

        if len(partes) > 1:

            match = re.match(
                r"(\d+)w",
                partes[1]
            )

            if match:
                tamanho = int(
                    match.group(1)
                )

        candidatos.append(
            (tamanho, url)
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

    elif isinstance(
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

    elif isinstance(
        valor,
        dict
    ):

        for chave in (
            "url",
            "contentUrl",
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


def extrair_jsonld_imagem(
    pagina_url,
    texto
):

    padrao = re.compile(
        r'<script[^>]+type=["\']'
        r'application/ld\+json["\'][^>]*>'
        r"(.*?)"
        r"</script>",
        flags=re.I | re.S
    )

    def procurar(obj):

        if isinstance(
            obj,
            dict
        ):

            for chave, valor in obj.items():

                if str(
                    chave
                ).lower() == "image":

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

        try:

            dados = json.loads(
                html.unescape(
                    bloco
                ).strip()
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

        r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)',

        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',

        r'<meta[^>]+(?:property|name)=["\']og:image:url["\'][^>]+content=["\']([^"\']+)',

        r'<meta[^>]+(?:property|name)=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',

        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']twitter:image["\']',

        r'<meta[^>]+(?:property|name)=["\']twitter:image:src["\'][^>]+content=["\']([^"\']+)',

        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)',
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


def imagem_da_tag_img(
    pagina_url,
    texto
):

    padrao = re.compile(
        r"<img\b([^>]+)>",
        flags=re.I | re.S
    )

    for bloco in padrao.findall(
        texto
    ):

        atributos = {}

        encontrados = re.findall(
            r'([a-zA-Z0-9_:-]+)\s*=\s*["\']([^"\']*)["\']',
            bloco,
            flags=re.I
        )

        for nome, valor in encontrados:

            atributos[
                nome.lower()
            ] = html.unescape(
                valor
            ).strip()

        for nome in (
            "srcset",
            "data-srcset",
        ):

            if atributos.get(nome):

                url = escolher_srcset(
                    atributos[nome]
                )

                if url:

                    return urljoin(
                        pagina_url,
                        url
                    )

        for nome in (
            "src",
            "data-src",
            "data-lazy-src",
            "data-original",
            "data-image",
            "data-lazy",
        ):

            valor = atributos.get(
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


def extrair_imagem_pagina(url):

    texto, url_final = baixar(
        url
    )

    if not texto:
        return ""

    imagem = extrair_jsonld_imagem(
        url_final,
        texto
    )

    if imagem:
        return imagem

    imagem = extrair_imagem_meta(
        url_final,
        texto
    )

    if imagem:
        return imagem

    return imagem_da_tag_img(
        url_final,
        texto
    )


def extrair_imagem_rss(
    item,
    base_url
):

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
                    html.unescape(
                        url
                    )
                )

                if imagem_valida(url):
                    return url

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
                    html.unescape(
                        url
                    )
                )

                if imagem_valida(url):
                    return url

    return ""


# =========================================================
# FILTRO DE PORTUGUÊS
# =========================================================

def parece_portugues(
    titulo,
    resumo
):

    texto = (
        f"{titulo} {resumo}"
    ).lower()

    # Caracteres muito comuns no português
    if re.search(
        r"[ãõáéíóúâêôç]",
        texto
    ):
        return True

    palavras = (
        " o ",
        " a ",
        " os ",
        " as ",
        " de ",
        " do ",
        " da ",
        " dos ",
        " das ",
        " em ",
        " para ",
        " com ",
        " por ",
        " que ",
        " uma ",
        " um ",
        " não ",
        " novo ",
        " nova ",
        " novos ",
        " novas ",
        " jogo ",
        " jogos ",
        " lançamento ",
        " lançamento",
        " anuncia ",
        " anunciado ",
        " revelou ",
        " revela ",
        " chega ",
        " poderá ",
        " pode ",
        " será ",
        " grátis ",
        " gratuito ",
        " gratuita ",
        " jogadores ",
        " desenvolvedora ",
        " desenvolvedor ",
        " atualização ",
    )

    encontrados = sum(
        1
        for palavra in palavras
        if palavra in f" {texto} "
    )

    return encontrados >= 2


# =========================================================
# CATEGORIA
# =========================================================

def descobrir_categoria(
    titulo,
    resumo,
    padrao
):

    texto = (
        f"{titulo} {resumo}"
    ).lower()

    if any(
        x in texto
        for x in (
            "playstation",
            "ps5",
            "ps4",
            "ps vr",
        )
    ):
        return "PlayStation"

    if any(
        x in texto
        for x in (
            "xbox",
            "game pass",
            "microsoft",
        )
    ):
        return "Xbox"

    if any(
        x in texto
        for x in (
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
        x in texto
        for x in (
            "pc",
            "steam",
            "epic games",
            "windows",
            "nvidia",
            "amd",
        )
    ):
        return "Pc"

    return padrao or "Notícias"


# =========================================================
# BUSCAR RSS
# =========================================================

def buscar_rss(fonte):

    print(
        f"\n[RSS] {fonte['nome']}: "
        f"{fonte['url']}"
    )

    texto, url_final = baixar(
        fonte["url"]
    )

    if not texto:
        return []

    try:

        raiz = ET.fromstring(
            texto
        )

    except Exception as erro:

        print(
            f"[ERRO] RSS inválido: "
            f"{erro}"
        )

        return []

    resultado = []

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

        titulo = titulo_item(
            item
        )

        link = link_item(
            item
        )

        resumo = descricao_item(
            item
        )

        data = data_item(
            item
        )

        if not titulo or not link:
            continue

        if not url_valida(link):
            continue

        # Bloqueia notícias em inglês.
        if not parece_portugues(
            titulo,
            resumo
        ):
            print(
                "[IGNORADA] "
                "Possível notícia em inglês:",
                titulo
            )
            continue

        if data is None:
            data = agora_utc()

        idade = (
            agora_utc() - data
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
            item,
            url_final
        )

        resultado.append({
            "titulo": titulo,
            "link": link,
            "resumo": resumo,
            "data": data,
            "imagem": imagem,
            "fonte": fonte["nome"],
            "categoria": fonte["categoria"],
        })

    print(
        f"[RSS] Encontradas "
        f"{len(resultado)} notícia(s) "
        f"em português."
    )

    return resultado


# =========================================================
# RESUMO E CONTEÚDO
# =========================================================

def criar_resumo(
    titulo,
    resumo,
    fonte
):

    resumo = limpar_html(
        resumo
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
# POSTS EXISTENTES
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
                "posts.json precisa ser "
                "uma lista."
            )

        return posts

    except FileNotFoundError:

        return []

    except json.JSONDecodeError as erro:

        raise ValueError(
            f"JSON inválido: {erro}"
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


def chaves_posts(posts):

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

        link = normalizar_url(
            post.get(
                "link",
                ""
            )
        )

        titulo = slug(
            post.get(
                "titulo",
                ""
            )
        )

        if post_id:
            ids.add(
                post_id
            )

        if link:
            links.add(
                link.rstrip("/")
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
# CRIAR POST
# =========================================================

def criar_post(noticia):

    titulo = noticia[
        "titulo"
    ]

    link = noticia[
        "link"
    ]

    fonte = noticia[
        "fonte"
    ]

    data = noticia.get(
        "data"
    ) or agora_utc()

    data_str = data_brasil(
        data
    )

    resumo = criar_resumo(
        titulo,
        noticia.get(
            "resumo",
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

    if not imagem:

        print(
            "[IMAGEM] Procurando "
            "imagem na página original..."
        )

        imagem = extrair_imagem_pagina(
            link
        )

    if imagem:

        print(
            "[IMAGEM] OK:",
            imagem
        )

    else:

        print(
            "[IMAGEM] Não encontrada."
        )

    post_id = (
        f"{data.strftime('%Y%m%d')}-"
        f"{slug(titulo)}"
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
# PRINCIPAL
# =========================================================

def main():

    print("=" * 60)

    print(
        "CavaloGameNews - "
        "Bot de notícias em português"
    )

    print("=" * 60)

    posts = carregar_posts()

    (
        ids,
        links,
        titulos
    ) = chaves_posts(
        posts
    )

    noticias = []

    for fonte in FONTES:

        try:

            noticias.extend(
                buscar_rss(
                    fonte
                )
            )

        except Exception as erro:

            print(
                f"[ERRO] {fonte['nome']}: "
                f"{erro}"
            )

    noticias.sort(
        key=lambda n: n["data"],
        reverse=True
    )

    novas = []

    for noticia in noticias:

        if len(novas) >= MAX_NOTICIAS:
            break

        link = normalizar_url(
            noticia["link"]
        )

        titulo = noticia[
            "titulo"
        ].strip()

        if (
            link.rstrip("/")
            in links
        ):
            continue

        if slug(titulo) in titulos:
            continue

        post = criar_post(
            noticia
        )

        if post["id"] in ids:
            continue

        novas.append(
            post
        )

        ids.add(
            post["id"]
        )

        links.add(
            link.rstrip("/")
        )

        titulos.add(
            slug(titulo)
        )

        print(
            "[NOVA]",
            titulo
        )

    if not novas:

        print(
            "\nNenhuma notícia nova "
            "em português encontrada."
        )

        return

    posts = novas + posts

    posts = posts[:MAX_POSTS]

    salvar_posts(
        posts
    )

    print("=" * 60)

    print(
        f"{len(novas)} notícia(s) "
        "adicionada(s)."
    )

    print(
        f"{len(posts)} posts no total."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
