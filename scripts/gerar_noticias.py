import json
import os
import html
import re


# ==============================
# CONFIGURAÇÕES
# ==============================

ARQUIVO_JSON = "posts.json"
PASTA_SAIDA = "noticias"


# ==============================
# ESCAPAR HTML
# ==============================

def escapar(texto):
    if texto is None:
        return ""

    return html.escape(str(texto))


# ==============================
# SLUG
# ==============================

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
# URL
# ==============================

def eh_url(url):

    if not url:
        return False

    url = str(url).strip().lower()

    return (
        url.startswith("http://")
        or
        url.startswith("https://")
    )


# ==============================
# YOUTUBE
# ==============================

def youtube_id(video):

    if not video:
        return None

    video = str(video).strip()


    # ID direto do YouTube
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", video):

        return video


    padroes = [

        r"youtube\.com/watch\?v=([^&]+)",

        r"youtube\.com/watch/([^?&]+)",

        r"youtu\.be/([^?&]+)",

        r"youtube\.com/embed/([^?&]+)",

        r"youtube\.com/shorts/([^?&]+)",

        r"youtube-nocookie\.com/embed/([^?&]+)"

    ]


    for padrao in padroes:

        resultado = re.search(
            padrao,
            video,
            re.IGNORECASE
        )

        if resultado:

            return resultado.group(1)


    return None


# ==============================
# CAMINHO DOS ARQUIVOS
# ==============================

def caminho_recurso(caminho):

    if not caminho:
        return ""

    caminho = str(caminho).strip()


    # URL externa
    if eh_url(caminho):

        return caminho


    # Corrigir barras
    caminho = caminho.replace("\\", "/")


    # Remover ./ do começo
    if caminho.startswith("./"):

        caminho = caminho[2:]


    # Se já possui ../
    if caminho.startswith("../"):

        return caminho


    # A página fica dentro de /noticias/
    #
    # Exemplo:
    #
    # videos/gta.mp4
    #
    # vira:
    #
    # ../videos/gta.mp4

    return "../" + caminho


# ==============================
# VÍDEOS
# ==============================

def gerar_videos(videos):

    if not videos:

        return ""


    # Caso seja apenas uma string

    if isinstance(videos, str):

        videos = [videos]


    resultado = ""


    for video in videos:

        if not video:

            continue


        video = str(video).strip()


        if not video:

            continue


        # ==============================
        # YOUTUBE
        # ==============================

        video_id = youtube_id(video)


        if video_id:

            resultado += f"""

            <div class="video-container">

                <iframe

                    src="https://www.youtube.com/embed/{escapar(video_id)}"

                    title="Vídeo da notícia"

                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"

                    allowfullscreen>

                </iframe>

            </div>

            """

            continue


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

            caminho = caminho_recurso(video)


            extensao = os.path.splitext(
                video.lower()
            )[1]


            tipos_video = {

                ".mp4": "video/mp4",

                ".webm": "video/webm",

                ".ogg": "video/ogg",

                ".mov": "video/quicktime",

                ".m4v": "video/mp4"

            }


            tipo_video = tipos_video.get(

                extensao,

                "video/mp4"

            )


            resultado += f"""

            <div class="video-container">

                <video

                    controls

                    preload="metadata"

                    playsinline>

                    <source

                        src="{escapar(caminho)}"

                        type="{tipo_video}">

                    Seu navegador não suporta vídeos.

                </video>

            </div>

            """


    if not resultado:

        return ""


    return f"""

    <div class="videos-container">

        {resultado}

    </div>

    """


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

            <p>

                {escapar(item)}

            </p>

            """

            continue


        if not isinstance(item, dict):

            continue


        tipo = item.get(

            "tipo",

            ""

        ).lower()


        # ==============================
        # TEXTO
        # ==============================

        if tipo in (

            "texto",

            "paragrafo"

        ):

            texto = item.get(

                "texto",

                ""

            )


            resultado += f"""

            <p>

                {escapar(texto)}

            </p>

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

            <h2>

                {escapar(texto)}

            </h2>

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

            <h3>

                {escapar(texto)}

            </h3>

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

                caminho_imagem = caminho_recurso(

                    imagem

                )


                if legenda:

                    legenda_html = f"""

                    <figcaption>

                        {escapar(legenda)}

                    </figcaption>

                    """

                else:

                    legenda_html = ""


                resultado += f"""

                <figure>

                    <img

                        src="{escapar(caminho_imagem)}"

                        alt="{escapar(legenda)}">

                    {legenda_html}

                </figure>

                """


        # ==============================
        # VÍDEO DENTRO DO CONTEÚDO
        # ==============================

        elif tipo == "video":


            videos = item.get(

                "videos",

                []

            )


            if not videos:

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


                if video:

                    videos = [video]


            resultado += gerar_videos(

                videos

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

                <li>

                    {escapar(lista_item)}

                </li>

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

            <strong>

                {escapar(texto)}

            </strong>

            """


    return resultado


# ==============================
# GERAR HTML
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


    imagem = noticia.get(

        "imagem",

        ""

    )


    conteudo = noticia.get(

        "conteudo",

        []

    )


    # ==============================
    # CORPO
    # ==============================

    corpo = gerar_conteudo(

        conteudo

    )


    # ==============================
    # VÍDEOS PRINCIPAIS
    # ==============================

    videos = noticia.get(

        "videos",

        []

    )


    # Compatibilidade com "video"

    if not videos:

        video = noticia.get(

            "video",

            ""

        )


        if video:

            videos = [video]


    videos_html = gerar_videos(

        videos

    )


    # ==============================
    # IMAGEM PRINCIPAL
    # ==============================

    imagem_principal = ""


    if imagem:

        caminho_imagem = caminho_recurso(

            imagem

        )


        imagem_principal = f"""

        <div class="imagem-principal">

            <img

                src="{escapar(caminho_imagem)}"

                alt="{titulo}">

        </div>

        """


    # ==============================
    # HTML COMPLETO
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

    font-family:

        Arial,

        Helvetica,

        sans-serif;

    background: #111;

    color: #fff;

}}


header {{

    background: #0f1115;

    padding: 20px 30px;

    border-bottom:

        3px solid #00ff88;

}}


.header-container {{

    max-width: 1200px;

    margin: auto;

    display: flex;

    align-items: center;

    justify-content: space-between;

}}


.logo {{

    color: #fff;

    text-decoration: none;

    font-size: 24px;

    font-weight: bold;

}}


.logo span {{

    color: #00ff88;

}}


.voltar {{

    color: #00ff88;

    text-decoration: none;

    font-weight: bold;

}}


main {{

    width: 90%;

    max-width: 1000px;

    margin: 40px auto;

}}


.categoria {{

    color: #00ff88;

    font-size: 14px;

    font-weight: bold;

    text-transform: uppercase;

    margin-bottom: 10px;

}}


h1 {{

    font-size: 46px;

    line-height: 1.15;

    margin-bottom: 15px;

}}


.data {{

    color: #999;

    margin-bottom: 25px;

}}


.resumo {{

    color: #ccc;

    font-size: 19px;

    line-height: 1.7;

    margin-bottom: 30px;

}}


/* ==============================
   IMAGEM
============================== */

.imagem-principal {{

    width: 100%;

    margin-bottom: 30px;

}}


.imagem-principal img {{

    width: 100%;

    max-height: 560px;

    object-fit: cover;

    border-radius: 14px;

    display: block;

}}


/* ==============================
   ARTIGO
============================== */

.artigo {{

    max-width: 800px;

    margin: auto;

    font-size: 18px;

    line-height: 1.8;

}}


.artigo p {{

    color: #ddd;

    margin-bottom: 25px;

}}


.artigo h2 {{

    font-size: 28px;

    margin-top: 35px;

    margin-bottom: 20px;

    color: #fff;

}}


.artigo h3 {{

    font-size: 23px;

    margin-top: 30px;

    margin-bottom: 15px;

}}


.artigo ul {{

    margin-bottom: 25px;

}}


.artigo li {{

    margin-bottom: 10px;

}}


/* ==============================
   IMAGENS DO ARTIGO
============================== */

.artigo figure {{

    margin: 30px 0;

}}


.artigo figure img {{

    width: 100%;

    display: block;

    border-radius: 12px;

}}


.artigo figcaption {{

    color: #999;

    text-align: center;

    font-size: 14px;

    margin-top: 8px;

}}


/* ==============================
   VÍDEOS
============================== */

.videos-container {{

    width: 100%;

    max-width: 1000px;

    margin: 30px auto;

}}


.video-container {{

    width: 100%;

    aspect-ratio: 16 / 9;

    margin-bottom: 30px;

    border-radius: 14px;

    overflow: hidden;

    background: #000;

}}


.video-container iframe {{

    width: 100%;

    height: 100%;

    border: 0;

    display: block;

}}


.video-container video {{

    width: 100%;

    height: 100%;

    display: block;

    background: #000;

    object-fit: contain;

}}


/* ==============================
   BOTÃO
============================== */

.back-button {{

    display: inline-block;

    margin-top: 20px;

    background: #00ff88;

    color: #111;

    padding: 12px 20px;

    border-radius: 7px;

    text-decoration: none;

    font-weight: bold;

}}


/* ==============================
   RODAPÉ
============================== */

footer {{

    background: #1a1a1a;

    text-align: center;

    padding: 25px;

    margin-top: 50px;

    color: #888;

}}


/* ==============================
   CELULAR
============================== */

@media (max-width: 600px) {{

    h1 {{

        font-size: 30px;

    }}


    main {{

        width: 92%;

    }}


    .artigo {{

        font-size: 16px;

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

{data} · CavaloGameNews

</div>


{imagem_principal}


{videos_html}


<article class="artigo">

{corpo}

</article>


<a

    class="back-button"

    href="../index.html">

    ← Voltar para as notícias

</a>


</main>


<footer>

© 2026 CavaloGameNews -

Todos os direitos reservados.

</footer>


</body>

</html>
"""


# ==============================
# GERAR TODAS AS NOTÍCIAS
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

            "ERRO ao ler o posts.json:"

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

            "ERRO: posts.json precisa conter uma lista de notícias."

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
