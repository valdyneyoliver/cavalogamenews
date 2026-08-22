import json
import os
import html
import re
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://valdyneyoliver.github.io/cavalogamenews"

# =========================================================
# CARREGAR POSTS
# =========================================================

with open("posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

os.makedirs("noticias", exist_ok=True)


# =========================================================
# FUNÇÃO PARA PEGAR ID DO YOUTUBE
# =========================================================

def youtube_id(url):

    if not url:
        return ""

    url = url.strip()

    # Se já for apenas o ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed = urlparse(url)

        # youtube.com/watch?v=ID
        if "youtube.com" in parsed.netloc:
            query = parse_qs(parsed.query)

            if "v" in query:
                return query["v"][0]

        # youtu.be/ID
        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/").split("/")[0]

        # youtube.com/embed/ID
        if "/embed/" in parsed.path:
            return parsed.path.split("/embed/")[1].split("/")[0]

    except Exception:
        pass

    return ""


# =========================================================
# GERAR BLOCO DE VÍDEOS
# =========================================================

def gerar_videos(post):

    videos_html = ""

    # -----------------------------------------------------
    # NOVO FORMATO: "videos": [...]
    # -----------------------------------------------------

    videos = post.get("videos", [])

    if isinstance(videos, list):

        for video in videos:

            if not isinstance(video, dict):
                continue

            tipo = video.get("tipo", "").lower().strip()
            url = video.get("url", "").strip()

            if not url:
                continue

            # =========================
            # YOUTUBE
            # =========================

            if tipo == "youtube":

                video_id = youtube_id(url)

                if video_id:

                    videos_html += f"""
                    <div class="video-container">

                        <iframe
                            src="https://www.youtube.com/embed/{html.escape(video_id)}"
                            title="Vídeo da notícia"
                            loading="lazy"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                            allowfullscreen>
                        </iframe>

                    </div>
                    """

            # =========================
            # VÍDEO DO PC
            # =========================

            elif tipo in ["pc", "local", "arquivo"]:

                video_url = html.escape(url)

                videos_html += f"""
                <div class="video-container">

                    <video
                        controls
                        preload="metadata"
                    >

                        <source
                            src="../{video_url}"
                            type="video/mp4"
                        >

                        Seu navegador não suporta vídeo HTML5.

                    </video>

                </div>
                """

    # -----------------------------------------------------
    # COMPATIBILIDADE COM O FORMATO ANTIGO
    # -----------------------------------------------------

    # Se existir apenas:
    #
    # "video": "W_PmEPTvn7g"
    #
    # também funciona.

    elif post.get("video"):

        video_id = youtube_id(post.get("video", ""))

        if video_id:

            videos_html += f"""
            <div class="video-container">

                <iframe
                    src="https://www.youtube.com/embed/{html.escape(video_id)}"
                    title="Vídeo da notícia"
                    loading="lazy"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    allowfullscreen>
                </iframe>

            </div>
            """

    return videos_html


# =========================================================
# GERAR TODAS AS NOTÍCIAS
# =========================================================

for post in posts:

    post_id = post["id"]

    titulo = html.escape(
        post.get("titulo", "CavaloGameNews")
    )

    resumo = html.escape(
        post.get("resumo", "")
    )

    imagem = html.escape(
        post.get("imagem", "")
    )

    categoria = html.escape(
        post.get("categoria", "Notícias")
    )

    data = html.escape(
        post.get("data", "")
    )

    url = f"{BASE_URL}/noticias/{post_id}.html"


    # =====================================================
    # CONTEÚDO
    # =====================================================

    paragrafos = post.get(
        "conteudo",
        [post.get("resumo", "")]
    )

    conteudo_html = ""

    for paragrafo in paragrafos:

        conteudo_html += f"""
        <p>
            {html.escape(str(paragrafo))}
        </p>
        """


    # =====================================================
    # VÍDEOS
    # =====================================================

    videos_html = gerar_videos(post)


    # =====================================================
    # 3 ÚLTIMAS NOTÍCIAS
    # =====================================================

    relacionadas = [
        p for p in posts
        if p.get("id") != post_id
    ][:3]


    related_html = ""

    for related in relacionadas:

        related_id = html.escape(
            related.get("id", "")
        )

        related_titulo = html.escape(
            related.get(
                "titulo",
                "CavaloGameNews"
            )
        )

        related_imagem = html.escape(
            related.get("imagem", "")
        )

        related_categoria = html.escape(
            related.get(
                "categoria",
                "Notícias"
            )
        )

        related_data = html.escape(
            related.get("data", "")
        )


        related_html += f"""

        <a
            href="../noticias/{related_id}.html"
            class="related-card"
        >

            <img
                src="{related_imagem}"
                alt="{related_titulo}"
            >

            <div class="related-content">

                <div class="category">
                    {related_categoria}
                </div>

                <div class="related-date">
                    {related_data}
                </div>

                <h3>
                    {related_titulo}
                </h3>

            </div>

        </a>

        """


    # =====================================================
    # HTML DA NOTÍCIA
    # =====================================================

    pagina = f"""<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
{titulo} - CavaloGameNews
</title>


<meta
    name="description"
    content="{resumo}"
>


<!-- =================================================
     DISCORD / REDES SOCIAIS
================================================= -->

<meta
    property="og:type"
    content="article"
>

<meta
    property="og:title"
    content="{titulo}"
>

<meta
    property="og:description"
    content="{resumo}"
>

<meta
    property="og:image"
    content="{imagem}"
>

<meta
    property="og:url"
    content="{url}"
>

<meta
    property="og:site_name"
    content="CavaloGameNews"
>


<meta
    name="twitter:card"
    content="summary_large_image"
>

<meta
    name="twitter:title"
    content="{titulo}"
>

<meta
    name="twitter:description"
    content="{resumo}"
>

<meta
    name="twitter:image"
    content="{imagem}"
>


<style>

/* =================================================
   GERAL
================================================= */

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: Arial, sans-serif;
}}


body {{
    background: #111;
    color: #fff;
}}


/* =================================================
   HEADER
================================================= */

header {{
    background: #0f1115;
    padding: 20px 30px;
    border-bottom: 3px solid #00ff88;
}}


header a {{
    color: #00ff88;
    text-decoration: none;
    font-weight: bold;
}}


/* =================================================
   ARTIGO
================================================= */

.article {{
    width: 90%;
    max-width: 1000px;
    margin: 40px auto;
}}


.category {{
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


.info {{
    color: #999;
    margin-bottom: 25px;
}}


/* =================================================
   IMAGEM
================================================= */

.cover {{
    width: 100%;
    max-height: 560px;
    object-fit: cover;
    border-radius: 14px;
    display: block;
    margin-bottom: 30px;
}}


/* =================================================
   TEXTO
================================================= */

.text {{
    max-width: 800px;
    margin: auto;
}}


.text p {{
    color: #ddd;
    font-size: 18px;
    line-height: 1.8;
    margin-bottom: 25px;
}}


/* =================================================
   VÍDEOS
================================================= */

.video-container {{
    width: 100%;
    margin: 30px 0;
    aspect-ratio: 16 / 9;
}}


.video-container iframe {{
    width: 100%;
    height: 100%;
    border: 0;
    border-radius: 14px;
    display: block;
}}


.video-container video {{
    width: 100%;
    height: 100%;
    object-fit: contain;
    background: #000;
    border-radius: 14px;
    display: block;
}}


/* =================================================
   BOTÃO
================================================= */

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


/* =================================================
   MAIS NOTÍCIAS
================================================= */

.related {{
    margin-top: 50px;
    padding-top: 30px;
    border-top: 1px solid #333;
}}


.related h2 {{
    color: #00ff88;
    margin-bottom: 20px;
}}


.related-grid {{
    display: grid;
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap: 20px;
}}


.related-card {{
    background: #1b1b1b;
    border: 1px solid #333;
    border-radius: 10px;
    overflow: hidden;
    text-decoration: none;
    color: #fff;
    display: block;
    transition: 0.2s;
}}


.related-card:hover {{
    border-color: #00ff88;
    transform: translateY(-3px);
}}


.related-card img {{
    width: 100%;
    height: 130px;
    object-fit: cover;
    display: block;
}}


.related-content {{
    padding: 12px;
}}


.related-content h3 {{
    font-size: 17px;
    margin-top: 6px;
    line-height: 1.3;
}}


.related-date {{
    color: #888;
    font-size: 12px;
    margin-top: 5px;
}}


/* =================================================
   FOOTER
================================================= */

footer {{
    background: #1a1a1a;
    text-align: center;
    padding: 25px;
    margin-top: 50px;
    color: #888;
}}


/* =================================================
   CELULAR
================================================= */

@media (max-width: 600px) {{

    h1 {{
        font-size: 30px;
    }}

    .article {{
        width: 92%;
    }}

    .text p {{
        font-size: 16px;
    }}

}}

</style>

</head>


<body>


<header>

<a href="../index.html">
← Voltar para o CavaloGameNews
</a>

</header>


<main class="article">


<div class="category">
{categoria}
</div>


<h1>
{titulo}
</h1>


<div class="info">
{data} · CavaloGameNews
</div>


<img
    class="cover"
    src="{imagem}"
    alt="{titulo}"
>


<!-- =================================================
     VÍDEOS
================================================= -->

{videos_html}


<div class="text">


<!-- =================================================
     CONTEÚDO
================================================= -->

{conteudo_html}


<a
    class="back-button"
    href="../index.html"
>
← Voltar para as notícias
</a>


<!-- =================================================
     MAIS NOTÍCIAS
================================================= -->

<div class="related">

<h2>
Mais notícias
</h2>


<div class="related-grid">

{related_html}

</div>

</div>


</div>

</main>


<footer>

© 2026 CavaloGameNews -
Todos os direitos reservados.

</footer>


</body>

</html>
"""


    # =====================================================
    # SALVAR
    # =====================================================

    caminho = f"noticias/{post_id}.html"


    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(pagina)


print(
    f"{len(posts)} notícias geradas com sucesso!"
)
