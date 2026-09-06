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
