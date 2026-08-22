import json
import os
import html
import re
from urllib.parse import urlparse


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ARQUIVO_JSON = "noticias.json"
PASTA_SAIDA = "noticias"


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def escapar(texto):
    if texto is None:
        return ""

    return html.escape(str(texto), quote=True)


def slug(texto):
    texto = str(texto).lower()

    substituicoes = {
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

        "ç": "c"
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)

    texto = re.sub(r"[^a-z0-9]+", "-", texto)

    return texto.strip("-")


# ============================================================
# VERIFICAR URL
# ============================================================

def eh_url(valor):

    if not valor:
        return False

    valor = str(valor).strip().lower()

    return (
        valor.startswith("http://")
        or
        valor.startswith("https://")
    )


# ============================================================
# CAMINHO DE RECURSO
#
# Os HTML das notícias ficam dentro de:
#
# noticias/
#
# Portanto:
#
# videos/video.mp4
#
# vira:
#
# ../videos/video.mp4
#
# ============================================================

def caminho_recurso(caminho):

    if not caminho:
        return ""

    caminho = str(caminho).strip()

    # URL externa
    if eh_url(caminho):
        return caminho

    # Corrigir barras
    caminho = caminho.replace("\\", "/")

    # Remover ./ inicial
    while caminho.startswith("./"):
        caminho = caminho[2:]

    # Se já estiver correto para a página
    if caminho.startswith("../"):
        return caminho

    # Caminho local relativo à raiz do site
    return "../" + caminho


# ============================================================
# YOUTUBE
# ============================================================

def youtube_id(valor):

    if not valor:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    # --------------------------------------------------------
    # Se já for apenas o ID do YouTube
    # Exemplo:
    #
    # dwuZB-3FGyg
    # --------------------------------------------------------

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", valor):
        return valor

    # --------------------------------------------------------
    # youtube.com/watch?v=
    # --------------------------------------------------------

    padroes = [

        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/watch\?.*?v=)([A-Za-z0-9_-]{11})",

        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",

        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",

        r"(?:youtube-nocookie\.com/embed/)([A-Za-z0-9_-]{11})"
    ]

    for padrao in padroes:

        resultado = re.search(
            padrao,
            valor,
            re.IGNORECASE
        )

        if resultado:
            return resultado.group(1)

    return None


# ============================================================
# IDENTIFICAR VÍDEO LOCAL
# ============================================================

def eh_video_local(valor):

    if not valor:
        return False

    valor = str(valor).strip().lower()

    extensoes = (
        ".mp4",
        ".webm",
        ".ogg",
        ".mov",
        ".m4v"
    )

    return valor.endswith(extensoes)


# ============================================================
# TIPO DO VÍDEO
# ============================================================

def tipo_video(caminho):

    extensao = os.path.splitext(
        caminho.lower()
    )[1]

    tipos = {

        ".mp4": "video/mp4",

        ".webm": "video/webm",

        ".ogg": "video/ogg",

        ".mov": "video/quicktime",

        ".m4v": "video/mp4"
    }

    return tipos.get(
        extensao,
        "video/mp4"
    )


# ============================================================
# GERAR VÍDEOS
# ============================================================

def gerar_videos(videos):

    if not videos:
        return ""

    # Se for apenas uma string
    if isinstance(videos, str):
        videos = [videos]

    if not isinstance(videos, list):
        return ""

    resultado = ""

    for video in videos:

        if video is None:
            continue

        video = str(video).strip()

        if not video:
            continue


        # ====================================================
        # YOUTUBE
        # ====================================================

        video_id = youtube_id(video)

        if video_id:

            resultado += f"""

<div class="video-container">

    <iframe
        src="https://www.youtube.com/embed/{escapar(video_id)}"
        title="Vídeo da notícia"
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen>
    </iframe>

</div>

"""

            continue


        # ====================================================
        # VÍDEO LOCAL DO PC
        # ====================================================

        if eh_video_local(video):

            caminho = caminho_recurso(video)

            mime = tipo_video(video)

            resultado += f"""

<div class="video-container">

    <video
        controls
        preload="metadata"
        playsinline
        controlsList="nodownload">

        <source
            src="{escapar(caminho)}"
            type="{mime}">

        Seu navegador não suporta vídeos HTML5.

    </video>

</div>

"""

            continue


        # ====================================================
        # URL DE VÍDEO EXTERNA
        # ====================================================

        if eh_url(video):

            resultado += f"""

<div class="video-container">

    <video
        controls
        preload="metadata"
        playsinline>

        <source
            src="{escapar(video)}"
            type="video/mp4">

        Seu navegador não suporta vídeos HTML5.

    </video>

</div>

"""

            continue


    return resultado


# ============================================================
# GERAR CONTEÚDO
# ============================================================

def gerar_conteudo(conteudo):

    if not conteudo:
        return ""

    # --------------------------------------------------------
    # Caso alguém coloque uma string
    # --------------------------------------------------------

    if isinstance(conteudo, str):

        return f"""
<p>{escapar(conteudo)}</p>
"""


    resultado = ""


    for item in conteudo:

        # ====================================================
        # TEXTO SIMPLES
        # ====================================================

        if isinstance(item, str):

            resultado += f"""

<p>
    {escapar(item)}
</p>

"""

            continue


        if not isinstance(item, dict):
            continue


        tipo = str(
            item.get("tipo", "")
        ).lower().strip()


        # ====================================================
        # TEXTO
        # ====================================================

        if tipo in ("texto", "paragrafo"):

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""

<p>
    {escapar(texto)}
</p>

"""


        # ====================================================
        # TÍTULO
        # ====================================================

        elif tipo == "titulo":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""

<h2>
    {escapar(texto)}
</h2>

"""


        # ====================================================
        # SUBTÍTULO
        # ====================================================

        elif tipo == "subtitulo":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""

<h3>
    {escapar(texto)}
</h3>

"""


        # ====================================================
        # IMAGEM
        # ====================================================

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

                caminho = caminho_recurso(
                    imagem
                )

                resultado += f"""

<figure>

    <img
        src="{escapar(caminho)}"
        alt="{escapar(legenda)}">

    {
        f'<figcaption>{escapar(legenda)}</figcaption>'
        if legenda
        else ""
    }

</figure>

"""


        # ====================================================
        # VÍDEO DENTRO DO CONTEÚDO
        # ====================================================

        elif tipo == "video":

            videos = item.get(
                "videos",
                []
            )

            # Compatibilidade
            if not videos:

                video = item.get(
                    "video",
                    ""
                )

                if video:
                    videos = [video]


            # Compatibilidade com url
            if not videos:

                video = item.get(
                    "url",
                    ""
                )

                if video:
                    videos = [video]


            # Compatibilidade com src
            if not videos:

                video = item.get(
                    "src",
                    ""
                )

                if video:
                    videos = [video]


            resultado += gerar_videos(
                videos
            )


        # ====================================================
        # LISTA
        # ====================================================

        elif tipo == "lista":

            itens = item.get(
                "itens",
                []
            )

            resultado += "<ul>"

            for lista_item in itens:

                resultado += f"""

<li>
    {escapar(lista_item)}
</li>

"""

            resultado += "</ul>"


        # ====================================================
        # NEGRITO
        # ====================================================

        elif tipo == "negrito":

            texto = item.get(
                "texto",
                ""
            )

            resultado += f"""

<strong>
    {escapar(texto)}
</strong>

"""


    return resultado


# ============================================================
# GERAR HTML DA NOTÍCIA
# ============================================================

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


    imagem = noticia.get(
        "imagem",
        ""
    )


    conteudo = noticia.get(
        "conteudo",
        []
    )


    # ========================================================
    # CONTEÚDO
    # ========================================================

    corpo = gerar_conteudo(
        conteudo
    )


    # ========================================================
    # VÍDEOS
    #
    # Aceita:
    #
    # "videos": [
    #   "dwuZB-3FGyg",
    #   "videos/meuvideo.mp4"
    # ]
    #
    # ========================================================

    videos = noticia.get(
        "videos",
        []
    )


    # Compatibilidade com "video"
    if not videos:

        video_antigo = noticia.get(
            "video",
            ""
        )

        if video_antigo:

            videos = [
                video_antigo
            ]


    videos_html = gerar_videos(
        videos
    )


    # ========================================================
    # IMAGEM PRINCIPAL
    # ========================================================

    imagem_html = ""

    if imagem:

        caminho_imagem = caminho_recurso(
            imagem
        )

        imagem_html = f"""

<div class="imagem-principal">

    <img
        src="{escapar(caminho_imagem)}"
        alt="{titulo}"
        loading="eager">

</div>

"""


    # ========================================================
    # HTML COMPLETO
    # ========================================================

    return f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0">

<title>
    {titulo} - CavaloGameNews
</title>

<meta
    name="description"
    content="{resumo}">

<style>

* {{
    box-sizing: border-box;
}}

body {{

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #0f0f0f;

    color: #ffffff;

}}


header {{

    background: #111111;

    border-bottom:
        1px solid #292929;

    padding:
        18px 20px;

}}


.header-container {{

    max-width:
        1200px;

    margin:
        auto;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

}}


.logo {{

    color:
        #ffffff;

    text-decoration:
        none;

    font-size:
        24px;

    font-weight:
        bold;

}}


.logo span {{

    color:
        #00ff88;

}}


.voltar {{

    color:
        #ffffff;

    text-decoration:
        none;

    padding:
        10px 16px;

    border-radius:
        8px;

    background:
        #222222;

    transition:
        0.2s;

}}


.voltar:hover {{

    background:
        #00ff88;

    color:
        #111111;

}}


main {{

    max-width:
        900px;

    margin:
        40px auto;

    padding:
        0 20px;

}}


.categoria {{

    display:
        inline-block;

    background:
        #00ff88;

    color:
        #111111;

    padding:
        6px 12px;

    border-radius:
        6px;

    font-size:
        13px;

    font-weight:
        bold;

    margin-bottom:
        15px;

}}


h1 {{

    font-size:
        42px;

    line-height:
        1.15;

    margin:
        0 0 15px;

}}


.data {{

    color:
        #999999;

    margin-bottom:
        25px;

}}


.resumo {{

    font-size:
        19px;

    line-height:
        1.6;

    color:
        #cccccc;

    margin-bottom:
        30px;

}}


/* ==========================================================
   IMAGEM PRINCIPAL
   ========================================================== */

.imagem-principal {{

    width:
        100%;

    margin-bottom:
        30px;

}}


.imagem-principal img {{

    display:
        block;

    width:
        100%;

    max-height:
        550px;

    object-fit:
        cover;

    border-radius:
        12px;

}}


/* ==========================================================
   ARTIGO
   ========================================================== */

.artigo {{

    font-size:
        18px;

    line-height:
        1.8;

}}


.artigo p {{

    margin:
        0 0 22px;

}}


.artigo h2 {{

    font-size:
        28px;

    margin-top:
        35px;

    margin-bottom:
        15px;

}}


.artigo h3 {{

    font-size:
        23px;

    margin-top:
        30px;

}}


.artigo ul {{

    margin-bottom:
        25px;

}}


.artigo li {{

    margin-bottom:
        10px;

}}


/* ==========================================================
   IMAGENS DENTRO DA NOTÍCIA
   ========================================================== */

.artigo figure {{

    margin:
        30px 0;

}}


.artigo figure img {{

    display:
        block;

    width:
        100%;

    max-width:
        100%;

    border-radius:
        10px;

}}


.artigo figcaption {{

    text-align:
        center;

    color:
        #999999;

    font-size:
        14px;

    margin-top:
        8px;

}}


/* ==========================================================
   VÍDEOS
   ========================================================== */

.video-container {{

    position:
        relative;

    width:
        100%;

    aspect-ratio:
        16 / 9;

    margin:
        30px 0;

    overflow:
        hidden;

    border-radius:
        12px;

    background:
        #000000;

}}


.video-container iframe {{

    display:
        block;

    width:
        100%;

    height:
        100%;

    border:
        none;

}}


.video-container video {{

    display:
        block;

    width:
        100%;

    height:
        100%;

    object-fit:
        contain;

    background:
        #000000;

}}


/* ==========================================================
   RODAPÉ
   ========================================================== */

footer {{

    margin-top:
        60px;

    padding:
        30px 20px;

    text-align:
        center;

    color:
        #777777;

    border-top:
        1px solid #292929;

}}


/* ==========================================================
   CELULAR
   ========================================================== */

@media (max-width: 700px) {{

    h1 {{

        font-size:
            30px;

    }}

    .artigo {{

        font-size:
            16px;

    }}

    .header-container {{

        flex-direction:
            column;

        gap:
            15px;

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


{imagem_html}


{videos_html}


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


# ============================================================
# GERAR TODAS AS NOTÍCIAS
# ============================================================

def gerar_noticias():

    # --------------------------------------------------------
    # Verificar JSON
    # --------------------------------------------------------

    if not os.path.exists(
        ARQUIVO_JSON
    ):

        print()
        print(
            f"ERRO: arquivo '{ARQUIVO_JSON}' não encontrado."
        )
        print()

        return


    # --------------------------------------------------------
    # Ler JSON
    # --------------------------------------------------------

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

        print()
        print(
            "ERRO ao ler o noticias.json:"
        )

        print(
            erro
        )

        print()

        return


    # --------------------------------------------------------
    # Verificar formato
    # --------------------------------------------------------

    if not isinstance(
        noticias,
        list
    ):

        print()
        print(
            "ERRO: noticias.json precisa conter uma lista de notícias."
        )
        print()

        return


    # --------------------------------------------------------
    # Criar pasta
    # --------------------------------------------------------

    os.makedirs(
        PASTA_SAIDA,
        exist_ok=True
    )


    quantidade = 0


    # --------------------------------------------------------
    # Gerar notícias
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print()

    print(
        f"Concluído! {quantidade} notícia(s) gerada(s)."
    )

    print()


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":

    gerar_noticias()
