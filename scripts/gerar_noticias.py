import json
import os
import html
import re

# ==============================
# CONFIGURAÇÕES
# ==============================

ARQUIVO_JSON = "noticias.json"
PASTA_SAIDA = "noticias"

# ==============================
# FUNÇÕES
# ==============================

def escapar(texto):
    if texto is None:
        return ""
    return html.escape(str(texto))


def slug(texto):
    texto = str(texto).lower()
    texto = re.sub(r"[áàãâä]", "a", texto)
    texto = re.sub(r"[éèêë]", "e", texto)
    texto = re.sub(r"[íìîï]", "i", texto)
    texto = re.sub(r"[óòõôö]", "o", texto)
    texto = re.sub(r"[úùûü]", "u", texto)
    texto = re.sub(r"[ç]", "c", texto)
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")


# ==============================
# YOUTUBE
# ==============================

def youtube_id(url):

    if not url:
        return None

    url = str(url).strip()

    padroes = [
        r"(?:youtube\.com/watch\?v=)([^&]+)",
        r"(?:youtu\.be/)([^?&]+)",
        r"(?:youtube\.com/embed/)([^?&]+)",
        r"(?:youtube\.com/shorts/)([^?&]+)",
        r"(?:youtube-nocookie\.com/embed/)([^?&]+)"
    ]

    for padrao in padroes:

        resultado = re.search(
            padrao,
            url,
            re.IGNORECASE
        )

        if resultado:
            return resultado.group(1)

    return None


# ==============================
# VÍDEO
# ==============================

def gerar_video(video):

    if not video:
        return ""

    video = str(video).strip()

    # ==============================
    # YOUTUBE
    # ==============================

    video_id = youtube_id(video)

    if video_id:

        return f"""
        <div class="video-container youtube-video">

            <iframe
                src="https://www.youtube.com/embed/{escapar(video_id)}"
                title="Vídeo da notícia"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>

        </div>
        """

    # ==============================
    # VÍDEO LOCAL
    # ==============================

    extensoes = (
        ".mp4",
        ".webm",
        ".ogg",
        ".mov",
        ".m4v"
    )

    if video.lower().endswith(extensoes):

        # Remove ./ do começo caso exista
        video = video.replace("\\", "/")

        if video.startswith("./"):
            video = video[2:]

        # Se o vídeo já estiver dentro da pasta noticias,
        # não adiciona ../
        if video.startswith("noticias/"):

            caminho_video = video

        else:

            # Como a página está dentro de /noticias/,
            # precisamos voltar uma pasta.
            caminho_video = "../" + video

        return f"""
        <div class="video-container local-video">

            <video
                controls
                preload="metadata"
                playsinline>

                <source
                    src="{escapar(caminho_video)}"
                    type="video/{escapar(video.split('.')[-1].lower())}">

                Seu navegador não suporta vídeos.

            </video>

        </div>
        """

    return ""


# ==============================
# CONTEÚDO
# ==============================

def gerar_conteudo(conteudo):

    if not conteudo:
        return ""

    resultado = ""

    for item in conteudo:

        # ==============================
        # TEXTO SIMPLES
        # ==============================

        if isinstance(item, str):

            resultado += f"""
            <p>{escapar(item)}</p>
            """

            continue

        if not isinstance(item, dict):
            continue

        tipo = item.get(
            "tipo",
            ""
        ).lower()

        # ==============================
        # PARÁGRAFO
        # ==============================

        if tipo == "texto" or tipo == "paragrafo":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""
            <p>{escapar(texto)}</p>
            """

        # ==============================
        # TÍTULO
        # ==============================

        elif tipo == "titulo":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""
            <h2>{escapar(texto)}</h2>
            """

        # ==============================
        # SUBTÍTULO
        # ==============================

        elif tipo == "subtitulo":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""
            <h3>{escapar(texto)}</h3>
            """

        # ==============================
        # IMAGEM
        # ==============================

        elif tipo == "imagem":

            imagem = item.get(
                "imagem",
                ""
            )

            legenda = item.get(
                "legenda",
                ""
            )

            if imagem:

                resultado += f"""
                <figure>

                    <img
                        src="../{escapar(imagem)}"
                        alt="{escapar(legenda)}">

                    {
                        f'<figcaption>{escapar(legenda)}</figcaption>'
                        if legenda
                        else ''
                    }

                </figure>
                """

        # ==============================
        # VÍDEO
        # ==============================

        elif tipo == "video":

            video = item.get(
                "video",
                ""
            )

            if not video:

                video = item.get(
                    "url",
                    ""
                )

            if not video:

                video = item.get(
                    "src",
                    ""
                )

            resultado += gerar_video(
                video
            )

        # ==============================
        # LISTA
        # ==============================

        elif tipo == "lista":

            itens = item.get(
                "itens",
                []
            )

            resultado += "<ul>"

            for lista_item in itens:

                resultado += f"""
                <li>{escapar(lista_item)}</li>
                """

            resultado += "</ul>"

        # ==============================
        # NEGRITO
        # ==============================

        elif tipo == "negrito":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""
            <strong>{escapar(texto)}</strong>
            """

    return resultado


# ==============================
# MODELO HTML
# ==============================

def gerar_html(noticia):

    titulo = escapar(
        noticia.get(
            "titulo",
            "Sem título"
        )
    )

    categoria = escapar(
        noticia.get(
            "categoria",
            "Notícias"
        )
    )

    data = escapar(
        noticia.get(
            "data",
            ""
        )
    )

    resumo = escapar(
        noticia.get(
            "resumo",
            ""
        )
    )

    imagem = escapar(
        noticia.get(
            "imagem",
            ""
        )
    )

    conteudo = noticia.get(
        "conteudo",
        []
    )

    corpo = gerar_conteudo(
        conteudo
    )

    # ==============================
    # VÍDEO PRINCIPAL
    # ==============================

    video_principal = ""

    video = noticia.get(
        "video",
        ""
    )

    if video:

        video_principal = gerar_video(
            video
        )

    # ==============================
    # IMAGEM PRINCIPAL
    # ==============================

    imagem_principal = ""

    if imagem:

        imagem_principal = f"""
        <div class="imagem-principal">

            <img
                src="../{imagem}"
                alt="{titulo}">

        </div>
        """

    # ==============================
    # HTML
    # ==============================

    return f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{titulo} - CavaloGameNews</title>

<meta
    name="description"
    content="{resumo}">

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #0f0f0f;
    color: #ffffff;
}}

header {{
    background: #111111;
    border-bottom: 1px solid #292929;
    padding: 18px 20px;
}}

.header-container {{
    max-width: 1200px;
    margin: auto;

    display: flex;

    align-items: center;

    justify-content: space-between;
}}

.logo {{
    color: #ffffff;
    text-decoration: none;

    font-size: 24px;
    font-weight: bold;
}}

.logo span {{
    color: #ff6b00;
}}

.voltar {{
    color: #ffffff;
    text-decoration: none;

    padding: 10px 16px;

    border-radius: 8px;

    background: #222222;

    transition: 0.2s;
}}

.voltar:hover {{
    background: #ff6b00;
}}

main {{
    max-width: 900px;

    margin: 40px auto;

    padding: 0 20px;
}}

.categoria {{
    display: inline-block;

    background: #ff6b00;

    color: #ffffff;

    padding: 6px 12px;

    border-radius: 6px;

    font-size: 13px;

    font-weight: bold;

    margin-bottom: 15px;
}}

h1 {{
    font-size: 42px;

    line-height: 1.15;

    margin: 0 0 15px;
}}

.data {{
    color: #999999;

    margin-bottom: 25px;
}}

.resumo {{
    font-size: 19px;

    line-height: 1.6;

    color: #cccccc;

    margin-bottom: 30px;
}}

.imagem-principal {{
    width: 100%;

    margin-bottom: 30px;
}}

.imagem-principal img {{
    width: 100%;

    max-height: 550px;

    object-fit: cover;

    border-radius: 12px;
}}

.artigo {{
    font-size: 18px;

    line-height: 1.8;
}}

.artigo p {{
    margin: 0 0 22px;
}}

.artigo h2 {{
    font-size: 28px;

    margin-top: 35px;
}}

.artigo h3 {{
    font-size: 23px;

    margin-top: 30px;
}}

.artigo ul {{
    margin-bottom: 25px;
}}

.artigo li {{
    margin-bottom: 10px;
}}

.artigo figure {{
    margin: 30px 0;
}}

.artigo figure img {{
    width: 100%;

    border-radius: 10px;
}}

.artigo figcaption {{
    text-align: center;

    color: #999999;

    font-size: 14px;

    margin-top: 8px;
}}


/* ==============================
   VÍDEOS
   ============================== */

.video-container {{

    position: relative;

    width: 100%;

    aspect-ratio: 16 / 9;

    margin: 30px 0;

    overflow: hidden;

    border-radius: 12px;

    background: #000000;
}}

.video-container iframe {{

    width: 100%;

    height: 100%;

    border: none;
}}

.video-container video {{

    display: block;

    width: 100%;

    height: 100%;

    object-fit: contain;

    background: #000000;
}}


footer {{

    margin-top: 60px;

    padding: 30px 20px;

    text-align: center;

    color: #777777;

    border-top: 1px solid #292929;
}}

@media (max-width: 700px) {{

    h1 {{

        font-size: 30px;
    }}

    .artigo {{

        font-size: 16px;
    }}

    .header-container {{

        flex-direction: column;

        gap: 15px;
    }}

}}

</style>

</head>

<body>

<header>

<div class="header-container">

<a
    class="logo"
    href="../index.html">

    Cavalo<span>GameNews</span>

</a>

<a
    class="voltar"
    href="../index.html">

    ← Voltar

</a>

</div>

</header>

<main>

<div class="categoria">

{categoria}

</div>

<h1>

{titulo}

</h1>

<div class="data">

{data}

</div>

<div class="resumo">

{resumo}

</div>

{imagem_principal}

{video_principal}

<article class="artigo">

{corpo}

</article>

</main>

<footer>

© 2026 CavaloGameNews — Todas as notícias de games em um só lugar.

</footer>

</body>

</html>
"""


# ==============================
# GERAR NOTÍCIAS
# ==============================

def gerar_noticias():

    if not os.path.exists(
        ARQUIVO_JSON
    ):

        print(
            f"ERRO: arquivo {ARQUIVO_JSON} não encontrado."
        )

        return

    try:

        with open(
            ARQUIVO_JSON,
            "r",
            encoding="utf-8"
        ) as arquivo:

            noticias = json.load(
                arquivo
            )

    except Exception as erro:

        print(
            "ERRO ao ler o noticias.json:"
        )

        print(
            erro
        )

        return

    if not isinstance(
        noticias,
        list
    ):

        print(
            "ERRO: noticias.json precisa conter uma lista de notícias."
        )

        return

    os.makedirs(
        PASTA_SAIDA,
        exist_ok=True
    )

    quantidade = 0

    for noticia in noticias:

        if not isinstance(
            noticia,
            dict
        ):

            continue

        titulo = noticia.get(
            "titulo",
            "noticia"
        )

        identificador = noticia.get(
            "id",
            ""
        )

        if not identificador:

            identificador = slug(
                titulo
            )

        identificador = slug(
            identificador
        )

        if not identificador:

            identificador = "noticia"

        arquivo_saida = os.path.join(
            PASTA_SAIDA,
            identificador + ".html"
        )

        try:

            html_noticia = gerar_html(
                noticia
            )

            with open(
                arquivo_saida,
                "w",
                encoding="utf-8"
            ) as arquivo:

                arquivo.write(
                    html_noticia
                )

            quantidade += 1

            print(
                f"OK: {arquivo_saida}"
            )

        except Exception as erro:

            print(
                f"ERRO ao gerar '{titulo}': {erro}"
            )

    print()

    print(
        f"Concluído! {quantidade} notícia(s) gerada(s)."
    )


# ==============================
# EXECUTAR
# ==============================

if __name__ == "__main__":

    gerar_noticias()
```
