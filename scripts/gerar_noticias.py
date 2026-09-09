import json
import os
import html
import re
from urllib.parse import urlparse, parse_qs
from datetime import date
from xml.sax.saxutils import escape as xml_escape


# =========================================================
# CONFIGURAÇÕES
# =========================================================

BASE_URL = "https://valdyneyoliver.github.io/cavalogamenews"

POSTS_FILE = "posts.json"
NEWS_DIR = "noticias"
SITEMAP_FILE = "sitemap.xml"


# =========================================================
# CARREGAR POSTS
# =========================================================

with open(POSTS_FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)

if not isinstance(posts, list):
    raise ValueError(
        "O arquivo posts.json precisa conter uma lista de notícias."
    )


# =========================================================
# CRIAR PASTA NOTICIAS
# =========================================================

os.makedirs(NEWS_DIR, exist_ok=True)


# =========================================================
# PEGAR ID DO YOUTUBE
# =========================================================

def youtube_id(url):

    if not url:
        return ""

    url = str(url).strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed = urlparse(url)

        if "youtube.com" in parsed.netloc:
            query = parse_qs(parsed.query)

            if "v" in query:
                return query["v"][0]

        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/").split("/")[0]

        if "/embed/" in parsed.path:
            return parsed.path.split("/embed/")[1].split("/")[0]

    except Exception:
        pass

    return ""


# =========================================================
# GERAR VÍDEOS
# =========================================================

def gerar_videos(post):

    videos_html = ""

    videos = post.get("videos", [])

    # =====================================================
    # VÁRIOS VÍDEOS
    # =====================================================

    if isinstance(videos, list) and len(videos) > 0:

        for video in videos:

            if not isinstance(video, dict):
                continue

            tipo = str(
                video.get("tipo", "")
            ).lower().strip()

            url = str(
                video.get("url", "")
            ).strip()

            if not url or url == "xxx":
                continue

            # =================================================
            # YOUTUBE
            # =================================================

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

            # =================================================
            # VÍDEO DO PC
            # =================================================

            elif tipo in ["pc", "local", "arquivo"]:

                video_url = html.escape(
                    url,
                    quote=True
                )

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

    # =====================================================
    # FORMATO ANTIGO
    # =====================================================

    elif post.get("video"):

        video_id = youtube_id(
            post.get("video", "")
        )

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
# GERAR POST DO X
# =========================================================

def gerar_post_x(post):

    x_url = str(
        post.get("x", "")
    ).strip()

    if not x_url:
        return ""

    if x_url == "xxx":
        return ""

    # Aceita somente links do X/Twitter
    if not (
        "x.com/" in x_url
        or "twitter.com/" in x_url
    ):
        return ""

    x_url = html.escape(
        x_url,
        quote=True
    )

    return f"""
<div class="x-container">

<blockquote class="twitter-tweet">
    <a href="{x_url}"></a>
</blockquote>

</div>
"""


# =========================================================
# LISTA DAS PÁGINAS GERADAS
# =========================================================

generated_news_urls = []


# =========================================================
# GERAR TODAS AS NOTÍCIAS
# =========================================================

for post in posts:

    post_id = str(
        post.get("id", "")
    ).strip()

    if not post_id:
        continue

    titulo = html.escape(
        str(
            post.get(
                "titulo",
                "CavaloGameNews"
            )
        )
    )

    resumo = html.escape(
        str(
            post.get(
                "resumo",
                ""
            )
        )
    )

    imagem = html.escape(
        str(
            post.get(
                "imagem",
                ""
            )
        ),
        quote=True
    )

    categoria = html.escape(
        str(
            post.get(
                "categoria",
                "Notícia"
            )
        )
    )

    data = html.escape(
        str(
            post.get(
                "data",
                ""
            )
        )
    )

    # =====================================================
    # URL DA NOTÍCIA
    # =====================================================

    news_url = (
        f"{BASE_URL}/noticias/"
        f"{post_id}.html"
    )

    generated_news_urls.append(
        news_url
    )

    # =====================================================
    # CONTEÚDO
    # =====================================================

    paragrafos = post.get("conteudo")

    if not isinstance(paragrafos, list):

        paragrafos = [
            post.get(
                "resumo",
                ""
            )
        ]

    conteudo_html = ""

    # =====================================================
    # POST DO X
    # O X será inserido no meio do conteúdo.
    # =====================================================

    x_html = gerar_post_x(post)

    paragrafos_validos = [
        str(p).strip()
        for p in paragrafos
        if str(p).strip()
    ]

    # Divide o conteúdo aproximadamente ao meio.
    # Se houver poucos parágrafos, o X entra depois do primeiro.
    meio = len(paragrafos_validos) // 2

    if len(paragrafos_validos) > 1:
        meio = max(1, meio)

    for indice, paragrafo in enumerate(paragrafos_validos):

        texto = html.escape(paragrafo)

        # =================================================
        # TRANSFORMAR URLs EM LINKS CLICÁVEIS
        # =================================================

        texto = re.sub(
            r'(https?://[^\s<]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            texto
        )

        conteudo_html += f"""
<p>
{texto}
</p>
"""

        # Coloca o post do X no meio da notícia
        if x_html and indice + 1 == meio:
            conteudo_html += x_html

    # Se houver apenas 1 parágrafo, coloca o X depois dele.
    if x_html and len(paragrafos_validos) == 1:
        conteudo_html += x_html

    # =====================================================
    # VÍDEOS
    # O YouTube continua no final da notícia.
    # =====================================================

    videos_html = gerar_videos(post)

    # =====================================================
    # 3 ÚLTIMAS NOTÍCIAS
    # =====================================================

    relacionadas = [
        p for p in posts
        if str(p.get("id", "")).strip() != post_id
    ][:3]

    related_html = ""

    for related in relacionadas:

        related_id = html.escape(
            str(
                related.get(
                    "id",
                    ""
                )
            )
        )

        related_titulo = html.escape(
            str(
                related.get(
                    "titulo",
                    "CavaloGameNews"
                )
            )
        )

        related_imagem = html.escape(
            str(
                related.get(
                    "imagem",
                    ""
                )
            ),
            quote=True
        )

        related_categoria = html.escape(
            str(
                related.get(
                    "categoria",
                    "Notícia"
                )
            )
        )

        related_data = html.escape(
            str(
                related.get(
                    "data",
                    ""
                )
            )
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

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-8CNXSR7BXS"></script>

<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-8CNXSR7BXS');
</script>


<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<link
    rel="icon"
    type="image/png"
    href="../img/logo_cavalo.png"
>

<title>{titulo} - CavaloGameNews</title>

<meta
    name="description"
    content="{resumo}"
>


<!-- =================================================
     DISCORD / FACEBOOK / WHATSAPP
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
    content="{news_url}"
>

<meta
    property="og:site_name"
    content="CavaloGameNews"
>


<!-- =================================================
     TWITTER CARD
================================================= -->

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
    background: radial-gradient(circle at 50% -10%, rgba(0,255,136,.12), transparent 35%), #080b09;
    min-height: 100vh;
    color: #fff;
}}


/* =================================================
   HEADER
================================================= */

header {{
    background: rgba(8,11,9,.92);
    padding: 16px 30px;
    border-bottom: 1px solid rgba(0,255,136,.22);
    position: sticky;
    top: 0;
    z-index: 20;
    backdrop-filter: blur(14px);
}}


.top-back-button {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 11px 18px;
    background: #181b20;
    border: 1px solid #00ff88;
    border-radius: 999px;
    color: #00ff88;
    text-decoration: none;
    font-weight: bold;
    font-size: 15px;
    transition: all 0.2s ease;
}}

.top-back-button:hover {{
    background: #00ff88;
    color: #111;
    transform: translateX(-3px);
    box-shadow: 0 0 15px rgba(0, 255, 136, 0.25);
}}


/* =================================================
   ARTIGO
================================================= */

.article {{
    width: calc(100% - 40px);
    max-width: 1120px;
    margin: 55px auto 80px;
    background: rgba(12,16,14,.82);
    border: 1px solid #26322b;
    border-radius: 24px;
    padding: 42px;
    box-shadow: 0 25px 70px rgba(0,0,0,.35);
}}


.category {{
    color: #00ff88;
    font-size: 14px;
    font-weight: bold;
    text-transform: uppercase;
    margin-bottom: 10px;
}}


h1 {{
    font-size: clamp(38px, 5vw, 62px);
    line-height: 1.06;
    letter-spacing: -1.5px;
    margin: 18px 0 16px;
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
    border-radius: 18px;
    display: block;
    margin-bottom: 42px;
    box-shadow: 0 20px 45px rgba(0,0,0,.35);
}}


/* =================================================
   TEXTO
================================================= */

.text {{
    max-width: 800px;
    margin: auto;
}}


.text p {{
    color: #d9dfdc;
    font-size: 18px;
    line-height: 1.85;
    margin-bottom: 25px;
}}


/* =================================================
   LINKS DO CONTEÚDO
================================================= */

.text p a {{
    color: #00ff88;
    font-weight: bold;
    text-decoration: underline;
}}


.text p a:hover {{
    color: #00cc6d;
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
   POST DO X
================================================= */

.x-container {{
    width: 100%;
    max-width: 650px;
    margin: 35px auto;
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
        repeat(auto-fit, minmax(220px, 1fr));
    gap: 20px;
}}


.related-card {{
    background: linear-gradient(145deg,#151b18,#0e1210);
    border: 1px solid #26322b;
    border-radius: 16px;
    overflow: hidden;
    text-decoration: none;
    color: #fff;
    display: block;
    transition: 0.2s;
}}


.related-card:hover {{
    border-color: #00ff88;
    transform: translateY(-5px);
    box-shadow: 0 14px 35px rgba(0,0,0,.3);
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

/* =================================================
   VISUAL PROFISSIONAL — CAVALOGAMENEWS
================================================= */

body {{
    background:
        radial-gradient(circle at 50% 0%, rgba(0,255,136,0.10), transparent 34%),
        #080b09;
    color: #f5f5f5;
}}

header {{
    background: rgba(7,10,8,0.92);
    padding: 18px 30px;
    border-bottom: 1px solid rgba(0,255,136,0.35);
    box-shadow: 0 8px 30px rgba(0,0,0,0.25);
    backdrop-filter: blur(12px);
}}

.top-back-button {{
    background: rgba(18,24,20,0.9);
    border: 1px solid #26352c;
    border-radius: 999px;
    color: #ddd;
    padding: 10px 17px;
    font-size: 14px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.18);
}}

.top-back-button:hover {{
    background: #00ff88;
    border-color: #00ff88;
    color: #07100b;
}}

.article {{
    width: min(92%, 1120px);
    margin: 52px auto 70px;
}}

.category {{
    display: inline-block;
    color: #00ff88;
    background: rgba(0,255,136,0.08);
    border: 1px solid rgba(0,255,136,0.22);
    border-radius: 999px;
    padding: 7px 13px;
    font-size: 12px;
    letter-spacing: 0.8px;
    margin-bottom: 18px;
}}

h1 {{
    max-width: 1000px;
    font-size: clamp(34px, 5vw, 58px);
    line-height: 1.06;
    letter-spacing: -1.5px;
    margin-bottom: 18px;
}}

.info {{
    color: #8f9993;
    font-size: 14px;
    margin-bottom: 30px;
}}

.cover {{
    max-height: 620px;
    object-fit: cover;
    border-radius: 20px;
    border: 1px solid #26352c;
    box-shadow: 0 25px 70px rgba(0,0,0,0.40);
    margin-bottom: 42px;
}}

.text {{
    max-width: 820px;
}}

.text p {{
    color: #d8dedb;
    font-size: 18px;
    line-height: 1.85;
    margin-bottom: 24px;
}}

.text p:first-child {{
    color: #f1f4f2;
    font-size: 20px;
}}

.text p a {{
    color: #00ff88;
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
}}

.video-container {{
    margin: 38px 0;
    padding: 7px;
    background: #0c110e;
    border: 1px solid #26352c;
    border-radius: 18px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.28);
}}

.video-container iframe,
.video-container video {{
    border-radius: 12px;
}}

.x-container {{
    max-width: 680px;
    margin: 40px auto;
    padding: 4px;
    background: #0c110e;
    border: 1px solid #26352c;
    border-radius: 16px;
}}

.back-button {{
    margin-top: 35px;
    background: #00ff88;
    color: #06100a;
    padding: 12px 19px;
    border-radius: 999px;
    box-shadow: 0 8px 25px rgba(0,255,136,0.16);
    transition: 0.2s;
}}

.back-button:hover {{
    transform: translateY(-2px);
    box-shadow: 0 12px 30px rgba(0,255,136,0.25);
}}

.related {{
    margin-top: 70px;
    padding-top: 35px;
    border-top: 1px solid #26352c;
}}

.related h2 {{
    color: #fff;
    font-size: 25px;
    margin-bottom: 22px;
}}

.related h2::before {{
    content: "";
    display: inline-block;
    width: 4px;
    height: 24px;
    background: #00ff88;
    border-radius: 4px;
    margin-right: 10px;
    vertical-align: -4px;
}}

.related-grid {{
    gap: 18px;
}}

.related-card {{
    background: linear-gradient(145deg,#111713,#0b0f0c);
    border: 1px solid #26352c;
    border-radius: 14px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.22);
}}

.related-card:hover {{
    border-color: rgba(0,255,136,0.55);
    transform: translateY(-5px);
    box-shadow: 0 18px 38px rgba(0,0,0,0.30);
}}

.related-card img {{
    height: 145px;
}}

.related-content {{
    padding: 15px;
}}

footer {{
    background: #070907;
    border-top: 1px solid #1c2921;
    padding: 28px 20px;
    margin-top: 70px;
}}

@media (max-width: 600px) {{
    header {{ padding: 14px 18px; }}
    .article {{ width: 92%; margin-top: 35px; }}
    h1 {{ font-size: 34px; letter-spacing: -0.8px; }}
    .cover {{ border-radius: 14px; margin-bottom: 30px; }}
    .text p {{ font-size: 16px; line-height: 1.75; }}
    .text p:first-child {{ font-size: 18px; }}
    .video-container {{ margin: 28px 0; padding: 4px; border-radius: 13px; }}
    .related-grid {{ grid-template-columns: 1fr; }}
}

</style>

</head>


<body>


<header>

<a href="../index.html" class="top-back-button">
    <span>←</span>
    <span>Voltar para o CavaloGameNews</span>
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


<div class="text">

{conteudo_html}

<!-- =================================================
     VÍDEOS DO YOUTUBE / PC
     Ficam sempre no final da notícia.
================================================= -->

{videos_html}

</div>


<div class="text">

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


<!-- =================================================
     SCRIPT OFICIAL DO X
================================================= -->

<script
    async
    src="https://platform.twitter.com/widgets.js"
    charset="utf-8">
</script>


</body>

</html>
"""


    # =====================================================
    # SALVAR HTML
    # =====================================================

    caminho = (
        f"{NEWS_DIR}/{post_id}.html"
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(pagina)


# =========================================================
# GERAR SITEMAP.XML
# =========================================================

today = date.today().isoformat()

sitemap_urls = [

    f"{BASE_URL}/",
    f"{BASE_URL}/index.html",

]

sitemap_urls.extend(
    generated_news_urls
)


# Remover duplicados

sitemap_urls = list(
    dict.fromkeys(sitemap_urls)
)


# =========================================================
# MONTAR XML
# =========================================================

sitemap_lines = [

    '<?xml version="1.0" encoding="UTF-8"?>',

    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

]


for url in sitemap_urls:

    sitemap_lines.append(
        "  <url>"
    )

    sitemap_lines.append(
        f"    <loc>{xml_escape(url)}</loc>"
    )

    sitemap_lines.append(
        f"    <lastmod>{today}</lastmod>"
    )

    sitemap_lines.append(
        "  </url>"
    )


sitemap_lines.append(
    "</urlset>"
)


sitemap_content = "\n".join(
    sitemap_lines
)


# =========================================================
# SALVAR SITEMAP
# =========================================================

with open(
    SITEMAP_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        sitemap_content
    )


# =========================================================
# FINAL
# =========================================================

print(
    f"{len(posts)} notícias geradas com sucesso!"
)

print(
    f"{len(generated_news_urls)} páginas adicionadas ao sitemap.xml!"
)

print(
    f"Sitemap atualizado: {SITEMAP_FILE}"
)
