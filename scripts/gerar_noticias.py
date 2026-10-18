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
BASE_URL = "https://cavalogamenews.com.br"
POSTS_FILE = "posts.json"
NEWS_DIR = "noticias"
SITEMAP_FILE = "sitemap.xml"
LOGO_PATH = "../img/logo.png"
FAVICON_PATH = "../img/logo_cavalo.png"

with open(POSTS_FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)

if not isinstance(posts, list):
    raise ValueError("O arquivo posts.json precisa conter uma lista de notícias.")

os.makedirs(NEWS_DIR, exist_ok=True)


def youtube_id(url):
    if not url:
        return ""
    url = str(url).strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if "youtube.com" in host:
            query = parse_qs(parsed.query)
            if "v" in query:
                return query["v"][0]
        if "youtu.be" in host:
            return parsed.path.strip("/").split("/")[0]
        if "/embed/" in parsed.path:
            return parsed.path.split("/embed/")[1].split("/")[0]
    except Exception:
        pass
    return ""


def gerar_videos(post):
    videos_html = ""
    videos = post.get("videos", [])

    if isinstance(videos, list) and videos:
        for video in videos:
            if not isinstance(video, dict):
                continue
            tipo = str(video.get("tipo", "")).lower().strip()
            url = str(video.get("url", "")).strip()
            if not url or url == "xxx":
                continue

            if tipo == "youtube":
                video_id = youtube_id(url)
                if video_id:
                    videos_html += f"""
<div class="video-container">
  <iframe src="https://www.youtube-nocookie.com/embed/{html.escape(video_id, quote=True)}"
    title="Vídeo da notícia" loading="lazy"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen></iframe>
</div>
"""
            elif tipo in ["pc", "local", "arquivo"]:
                video_url = html.escape(url, quote=True)
                videos_html += f"""
<div class="video-container">
  <video controls preload="metadata">
    <source src="../{video_url}" type="video/mp4">
    Seu navegador não suporta vídeo HTML5.
  </video>
</div>
"""
    elif post.get("video"):
        video_id = youtube_id(post.get("video", ""))
        if video_id:
            videos_html += f"""
<div class="video-container">
  <iframe src="https://www.youtube-nocookie.com/embed/{html.escape(video_id, quote=True)}"
    title="Vídeo da notícia" loading="lazy"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen></iframe>
</div>
"""
    return videos_html


def gerar_post_x(post):
    x_url = str(post.get("x", "")).strip()
    if not x_url or x_url == "xxx":
        return ""
    if not ("x.com/" in x_url or "twitter.com/" in x_url):
        return ""
    x_url = html.escape(x_url, quote=True)
    return f"""
<div class="x-container">
  <blockquote class="twitter-tweet">
    <a href="{x_url}"></a>
  </blockquote>
</div>
"""


def escape_attr(value):
    return html.escape(str(value or ""), quote=True)


def renderizar_conteudo(post):
    paragrafos = post.get("conteudo")
    if not isinstance(paragrafos, list):
        paragrafos = [post.get("resumo", "")]

    validos = [
        p for p in paragrafos
        if isinstance(p, dict) or (isinstance(p, str) and p.strip())
    ]
    meio = max(1, len(validos) // 2) if len(validos) > 1 else len(validos)
    x_html = gerar_post_x(post)
    conteudo_html = ""

    for indice, item in enumerate(validos):
        if isinstance(item, dict):
            tipo = str(item.get("tipo", "")).lower().strip()
            url = str(item.get("url", "")).strip()

            if tipo in ["imagem", "image"]:
                if url:
                    alt = escape_attr(item.get("alt", "Imagem da notícia"))
                    legenda = str(item.get("legenda", "")).strip()
                    legenda_html = (
                        f"<figcaption>{html.escape(legenda)}</figcaption>"
                        if legenda else ""
                    )
                    conteudo_html += f"""
<figure class="content-image">
  <img src="{escape_attr(url)}" alt="{alt}" loading="lazy">
  {legenda_html}
</figure>
"""
                if x_html and indice + 1 == meio:
                    conteudo_html += x_html
                continue

            if tipo in ["youtube", "youtube_video"]:
                video_id = youtube_id(url)
                if video_id:
                    conteudo_html += f"""
<div class="video-container">
  <iframe src="https://www.youtube-nocookie.com/embed/{html.escape(video_id, quote=True)}"
    title="Vídeo da notícia" loading="lazy"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    allowfullscreen></iframe>
</div>
"""
                continue

            if tipo in ["x", "twitter"]:
                if url and url != "xxx" and ("x.com/" in url or "twitter.com/" in url):
                    safe_url = escape_attr(url)
                    conteudo_html += f"""
<div class="x-container">
  <blockquote class="twitter-tweet"><a href="{safe_url}"></a></blockquote>
</div>
"""
                continue

            if tipo in ["video", "pc", "local", "arquivo"] and url:
                conteudo_html += f"""
<div class="video-container">
  <video controls preload="metadata">
    <source src="../{escape_attr(url)}" type="video/mp4">
    Seu navegador não suporta vídeo HTML5.
  </video>
</div>
"""
                continue
            continue

        texto = html.escape(str(item).strip())
        texto = re.sub(
            r"\[verde\](.*?)\[/verde\]",
            r'<span class="texto-verde">\1</span>',
            texto,
            flags=re.IGNORECASE
        )
        texto = re.sub(
            r"\[titulo\](.*?)\[/titulo\]",
            r'<span class="paragrafo-titulo">\1</span>',
            texto,
            flags=re.IGNORECASE
        )
      texto = re.sub(
            r'(https?://[^\s<]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            texto
        )
        conteudo_html += f"<p>{texto}</p>\n"

        if x_html and indice + 1 == meio:
            conteudo_html += x_html

    if x_html and len(validos) == 1:
        conteudo_html += x_html
    return conteudo_html


generated_news_urls = []

for post in posts:
    post_id = str(post.get("id", "")).strip()
    if not post_id:
        continue

    titulo_texto = str(post.get("titulo", "CavaloGameNews"))
    resumo_texto = str(post.get("resumo", ""))
    imagem_texto = str(post.get("imagem", ""))
    categoria_texto = str(post.get("categoria", "Notícia"))
    data_texto = str(post.get("data", ""))

    titulo = html.escape(titulo_texto)
    resumo = html.escape(resumo_texto, quote=True)
    imagem = html.escape(imagem_texto, quote=True)
    categoria = html.escape(categoria_texto)
    data = html.escape(data_texto)

    news_url = f"{BASE_URL}/noticias/{post_id}.html"
    generated_news_urls.append(news_url)
    conteudo_html = renderizar_conteudo(post)
    videos_html = gerar_videos(post)

    # As primeiras notícias de posts.json são consideradas as mais recentes.
    relacionadas = [
        p for p in posts
        if str(p.get("id", "")).strip() != post_id
    ][:5]

    # A lateral mostra as 5 notícias seguintes.
    # A seção inferior mostra outras notícias, sem repetir as da lateral.
    relacionadas_lateral = relacionadas[:5]
    relacionadas_mais = relacionadas[5:8]

    def montar_cards(lista):
        cards_html = ""
        for related in lista:
            related_id = str(related.get("id", "")).strip()
            if not related_id:
                continue
            related_titulo = str(related.get("titulo", "CavaloGameNews"))
            related_imagem = str(related.get("imagem", ""))
            related_categoria = str(related.get("categoria", "Notícia"))
            related_data = str(related.get("data", ""))
            cards_html += f"""
<a href="../noticias/{escape_attr(related_id)}.html" class="related-card">
  <img src="{escape_attr(related_imagem)}" alt="{escape_attr(related_titulo)}" loading="lazy">
  <div class="related-content">
    <div class="category">{html.escape(related_categoria)}</div>
    <div class="related-date">{html.escape(related_data)}</div>
    <h3>{html.escape(related_titulo)}</h3>
  </div>
</a>
"""
        return cards_html

    related_html = montar_cards(relacionadas_lateral)
    more_html = montar_cards(relacionadas_mais)

    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0b0f14">
<title>{titulo} - CavaloGameNews</title>
<meta name="description" content="{resumo}">
<link rel="icon" type="image/png" href="{FAVICON_PATH}">

<!-- Google AdSense -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2309633346352325" crossorigin="anonymous"></script>

<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-8CNXSR7BXS"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-8CNXSR7BXS');
</script>

<!-- Open Graph -->
<meta property="og:type" content="article">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{resumo}">
<meta property="og:image" content="{imagem}">
<meta property="og:url" content="{news_url}">
<meta property="og:site_name" content="CavaloGameNews">

<!-- X/Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{titulo}">
<meta name="twitter:description" content="{resumo}">
<meta name="twitter:image" content="{imagem}">

<style>
:root {{
  color-scheme: dark;
  --bg: #0b0f14;
  --surface: #111820;
  --surface-2: #171f28;
  --text: #f2f5f7;
  --muted: #a2adb8;
  --border: #26313b;
  --accent: #00e887;
  --accent-strong: #00c875;
  --shadow: 0 14px 38px rgba(0,0,0,.22);
}}
html[data-theme="light"] {{
  color-scheme: light;
  --bg: #f2f5f7;
  --surface: #ffffff;
  --surface-2: #f7f9fa;
  --text: #18212a;
  --muted: #687581;
  --border: #dce3e8;
  --accent: #008f55;
  --accent-strong: #007747;
  --shadow: 0 14px 38px rgba(20,35,45,.08);
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.6;
  transition: background .2s ease, color .2s ease;
}}
a {{ color: inherit; }}
.site-header {{
  background: var(--surface);
  border-bottom: 3px solid var(--accent);
  box-shadow: var(--shadow);
}}
.header-inner {{
  width: min(1200px, 92%);
  min-height: 10px;
  margin: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  padding: 6px 0;
}}
.brand {{ display: inline-flex; align-items: center; text-decoration: none; min-width: 0; }}
.brand img {{ display: block; width: min(400px, 100%); max-height: 40px; object-fit: contain; }}
.header-actions {{ display: flex; align-items: center; gap: 10px; }}
.theme-toggle, .home-button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--text);
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  transition: transform .18s ease, border-color .18s ease, background .18s ease;
}}
.theme-toggle:hover, .home-button:hover {{
  border-color: var(--accent);
  transform: translateY(-2px);
}}
.support-overlay {{
  display: none;
  position: fixed;
  inset: 0;
  z-index: 99999;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.78);
  backdrop-filter: blur(5px);
}}

.support-overlay.is-open {{
  display: flex;
}}

.support-modal {{
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 30px 24px;
  border: 1px solid var(--accent);
  border-radius: 18px;
  background: var(--card);
  color: var(--text);
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
}}

.support-modal h2 {{
  margin: 0 0 12px;
  color: var(--accent);
  font-size: 25px;
}}

.support-modal p {{
  line-height: 1.6;
}}

.support-close {{
  position: absolute;
  top: 10px;
  right: 12px;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: transparent;
  color: var(--text);
  font-size: 24px;
  cursor: pointer;
}}

.pix-key {{
  display: block;
  margin: 20px 0 14px;
  padding: 14px 10px;
  overflow-wrap: anywhere;
  border: 1px dashed var(--accent);
  border-radius: 10px;
  background: var(--bg);
  font-weight: 700;
  user-select: all;
}}

.pix-qrcode {{
  display: block;
  width: 150px;
  max-width: 100%;
  height: auto;
  margin: 18px auto;
  padding: 8px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid var(--border);
}}

.copy-pix-button {{
  width: 100%;
  padding: 13px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: #06140d;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}}

.copy-pix-button:hover {{
  filter: brightness(1.08);
}}

.pix-feedback {{
  min-height: 24px;
  margin-bottom: 0;
  font-size: 14px;
}}
.support-button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  padding: 10px 14px;
  border: 1px solid var(--accent);
  border-radius: 10px;
  background: var(--accent);
  color: #06140d;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
  transition: transform .18s ease, background .18s ease;
}}

.support-button:hover {{
  background: var(--accent-strong);
  transform: translateY(-2px);
}}
.theme-toggle:focus-visible, .home-button:focus-visible,
.support-button:focus-visible, a:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}}
.page-wrap {{ width: min(1200px, 92%); margin: 32px auto 56px; }}
.breadcrumbs {{ color: var(--muted); font-size: 13px; margin-bottom: 20px; }}
.breadcrumbs a {{ color: var(--accent); text-decoration: none; }}
.layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 310px; gap: 28px; align-items: start; }}
.article-card, .sidebar-card {{
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: var(--shadow);
}}
.article-head {{ padding: 28px 30px 8px; }}
.category {{
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .09em;
  text-transform: uppercase;
  margin-bottom: 10px;
}}
h1 {{
  margin: 0 0 14px;
  font-size: clamp(30px, 4vw, 45px);
  line-height: 1.13;
  letter-spacing: -.025em;
  overflow-wrap: anywhere;
}}
.info {{ color: var(--muted); font-size: 13px; }}
.cover {{
  display: block;
  width: calc(100% - 60px);
  max-height: 560px;
  object-fit: cover;
  border-radius: 12px;
  margin: 22px 30px 28px;
  background: var(--surface-2);
}}
.text {{ padding: 0 30px 30px; overflow-wrap: anywhere; }}
.text p {{
  margin: 0 0 22px;
  color: var(--text);
  font-size: 18px;
  line-height: 1.85;
}}
.text p a {{ color: var(--accent); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }}
.text p a:hover {{ color: var(--accent-strong); }}
.texto-verde {{ color: var(--accent); font-weight: 800; }}
.paragrafo-titulo {{
  display: block;
  color: var(--accent);
  font-weight: 800;
  font-size: 21px;
  line-height: 1.4;
  margin-bottom: 8px;
}}
.content-image {{ width: 100%; margin: 28px auto; text-align: center; }}
.content-image img {{ width: 100%; height: auto; display: block; border-radius: 12px; }}
.content-image figcaption {{ color: var(--muted); font-size: 13px; margin-top: 8px; }}
.video-container {{
  width: 100%;
  aspect-ratio: 16 / 9;
  margin: 28px 0;
  overflow: hidden;
  border-radius: 12px;
  background: #000;
}}
.video-container iframe, .video-container video {{
  display: block; width: 100%; height: 100%; border: 0;
}}
.video-container video {{ object-fit: contain; }}
.x-container {{ width: 100%; max-width: 650px; margin: 28px auto; }}
.back-button {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  padding: 11px 16px;
  border-radius: 9px;
  background: var(--accent);
  color: #06140d;
  font-weight: 800;
  text-decoration: none;
  transition: transform .18s ease, background .18s ease;
}}
.back-button:hover {{ background: var(--accent-strong); transform: translateY(-2px); }}
.sidebar-card {{ padding: 20px; position: sticky; top: 20px; }}
.sidebar-title {{
  margin: 0 0 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
  font-size: 19px;
  line-height: 1.3;
}}
.sidebar-title::before {{ content: ""; display: inline-block; width: 4px; height: 19px; background: var(--accent); border-radius: 3px; margin-right: 9px; vertical-align: -3px; }}
.related-list {{ display: grid; gap: 14px; }}
.related-card {{
  display: grid;
  grid-template-columns: 94px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 10px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 11px;
  color: var(--text);
  text-decoration: none;
  transition: transform .18s ease, border-color .18s ease;
}}
.related-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
.related-card img {{
  display: block;
  width: 94px;
  height: 78px;
  object-fit: cover;
  border-radius: 7px;
  background: var(--border);
}}
.related-content {{ min-width: 0; }}
.related-content .category {{ font-size: 10px; margin: 0 0 3px; }}
.related-date {{ color: var(--muted); font-size: 11px; margin-bottom: 4px; }}
.related-content h3 {{ font-size: 13px; line-height: 1.35; margin: 0; overflow-wrap: anywhere; }}
.more-news {{
  margin-top: 30px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}}
.more-news h2 {{ color: var(--accent); margin: 0 0 16px; font-size: 22px; }}
.more-news .related-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
.more-news .related-card {{ display: block; padding: 0; overflow: hidden; }}
.more-news .related-card img {{ width: 100%; height: 135px; border-radius: 0; }}
.more-news .related-content {{ padding: 12px; }}
footer {{
  padding: 28px 4%;
  background: var(--surface);
  border-top: 1px solid var(--border);
  color: var(--muted);
  text-align: center;
  font-size: 13px;
}}
@media (max-width: 980px) {{
  .layout {{ grid-template-columns: minmax(0, 1fr) 275px; gap: 18px; }}
  .article-head {{ padding: 24px 24px 8px; }}
  .cover {{ width: calc(100% - 48px); margin: 20px 24px 24px; }}
  .text {{ padding: 0 24px 24px; }}
  .sidebar-card {{ padding: 15px; }}
  .related-card {{ grid-template-columns: 78px minmax(0, 1fr); gap: 9px; }}
  .related-card img {{ width: 78px; height: 68px; }}
}}
@media (max-width: 760px) {{
  .header-inner {{ width: 92%; min-height: 0; flex-wrap: wrap; gap: 12px; padding: 12px 0; }}
  .brand {{ flex: 1 1 100%; justify-content: center; }}
  .brand img {{ width: min(260px, 82vw); max-height: 66px; }}
  .header-actions {{ width: 100%; justify-content: space-between; }}
  .page-wrap {{ margin-top: 22px; }}
  .layout {{ grid-template-columns: minmax(0, 1fr); }}
  .sidebar-card {{ position: static; }}
  .related-list {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .related-card {{ display: block; padding: 0; overflow: hidden; }}
  .related-card img {{ width: 100%; height: 115px; border-radius: 0; }}
  .related-content {{ padding: 10px; }}
  .related-content h3 {{ font-size: 13px; }}
  .more-news .related-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 480px) {{
  .page-wrap {{ width: 94%; }}
  .article-head {{ padding: 21px 17px 5px; }}
  h1 {{ font-size: 29px; }}
  .cover {{ width: calc(100% - 34px); margin: 17px 17px 22px; border-radius: 9px; }}
  .text {{ padding: 0 17px 22px; }}
  .text p {{ font-size: 16px; line-height: 1.8; margin-bottom: 19px; }}
  .paragrafo-titulo {{ font-size: 19px; }}
  .related-list {{ grid-template-columns: minmax(0, 1fr); }}
  .related-card {{ display: grid; grid-template-columns: 100px minmax(0, 1fr); }}
  .related-card img {{ width: 100px; height: 82px; border-radius: 0; }}
  .more-news .related-grid {{ grid-template-columns: minmax(0, 1fr); }}
  .more-news .related-card {{ display: grid; grid-template-columns: 105px minmax(0, 1fr); }}
  .more-news .related-card img {{ width: 105px; height: 88px; }}
  .theme-toggle, .home-button {{ font-size: 13px; padding: 9px 11px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ scroll-behavior: auto !important; transition: none !important; }}
}}
</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="../index.html" aria-label="CavaloGameNews - página inicial">
      <img src="{LOGO_PATH}" alt="CavaloGameNews">
    </a>
    <div class="header-actions">
  <a class="home-button" href="../index.html">← Página inicial</a>

  <button class="support-button" id="supportButton" type="button">
    💚 Apoie
  </button>

  <button class="theme-toggle" id="themeToggle" type="button" aria-label="Alternar tema">
    <span id="themeIcon" aria-hidden="true">☀</span>
    <span id="themeLabel">Tema claro</span>
  </button>
</div>
  </div>
</header>
<div class="support-overlay" id="supportOverlay" aria-hidden="true">
  <div class="support-modal" role="dialog" aria-modal="true" aria-labelledby="supportTitle">
    <button class="support-close" id="supportClose" type="button" aria-label="Fechar janela">×</button>

    <h2 id="supportTitle">💚 Apoie o CavaloGameNews</h2>

    <p>
      Gostou das notícias? Ajude a manter o CavaloGameNews no ar
      e a trazer mais novidades sobre o mundo dos games!
    </p>

    <p>Você pode contribuir com qualquer valor usando Pix.</p>

    <span class="pix-key" id="pixKey">valdyneyoliver@gmail.com</span>

    <img
  class="pix-qrcode"
  src="../img/qrcode_pix_cavalogamenews.png"
  alt="QR Code Pix para apoiar o CavaloGameNews"
  loading="lazy"
>

    <button class="copy-pix-button" id="copyPix" type="button">
      Copiar chave Pix
    </button>

    <p class="pix-feedback" id="pixFeedback" aria-live="polite"></p>
  </div>
</div>

<main class="page-wrap">
  <div class="breadcrumbs"><a href="../index.html">Início</a> / {categoria}</div>
  <div class="layout">
    <article class="article-card">
      <div class="article-head">
        <div class="category">{categoria}</div>
        <h1>{titulo}</h1>
        <div class="info">{data} · CavaloGameNews</div>
      </div>
      <img class="cover" src="{imagem}" alt="{titulo}" fetchpriority="high">
      <div class="text">
        {conteudo_html}
        {videos_html}
        <a class="back-button" href="../index.html">← Voltar para as notícias</a>
      </div>
    </article>

    <aside class="sidebar-card" aria-label="Últimas notícias">
      <h2 class="sidebar-title">Últimas notícias</h2>
      <div class="related-list">
        {related_html}
      </div>
    </aside>
  </div>

</main>

<footer>© 2026 CavaloGameNews — Todos os direitos reservados.</footer>

<script>
(function() {{
  const root = document.documentElement;
  const button = document.getElementById('themeToggle');
  const icon = document.getElementById('themeIcon');
  const label = document.getElementById('themeLabel');

  function applyTheme(theme) {{
    root.setAttribute('data-theme', theme);
    const light = theme === 'light';
    icon.textContent = light ? '☾' : '☀';
    label.textContent = light ? 'Tema escuro' : 'Tema claro';
    button.setAttribute('aria-label', light ? 'Ativar tema escuro' : 'Ativar tema claro');
    try {{ localStorage.setItem('cgn-theme', theme); }} catch (e) {{}}
  }}

  let savedTheme = 'dark';
  try {{ savedTheme = localStorage.getItem('cgn-theme') || 'dark'; }} catch (e) {{}}
  applyTheme(savedTheme === 'light' ? 'light' : 'dark');

  button.addEventListener('click', function() {{
    applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  }});
}})();
</script>
<script>
(function() {{
  const openButton = document.getElementById('supportButton');
  const overlay = document.getElementById('supportOverlay');
  const closeButton = document.getElementById('supportClose');
  const copyButton = document.getElementById('copyPix');
  const pixKey = document.getElementById('pixKey');
  const feedback = document.getElementById('pixFeedback');

  if (!openButton || !overlay || !closeButton || !copyButton) return;

  function openModal() {{
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    closeButton.focus();
  }}

  function closeModal() {{
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    openButton.focus();
  }}

  openButton.addEventListener('click', openModal);
  closeButton.addEventListener('click', closeModal);

  overlay.addEventListener('click', function(event) {{
    if (event.target === overlay) {{
      closeModal();
    }}
  }});

  document.addEventListener('keydown', function(event) {{
    if (event.key === 'Escape' && overlay.classList.contains('is-open')) {{
      closeModal();
    }}
  }});

  copyButton.addEventListener('click', async function() {{
    try {{
      await navigator.clipboard.writeText(pixKey.textContent.trim());
      feedback.textContent = 'Chave Pix copiada com sucesso!';
    }} catch (error) {{
      feedback.textContent = 'Não foi possível copiar automaticamente. Selecione a chave e copie manualmente.';
    }}
  }});
}})();
</script>

<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body>
</html>
"""

    caminho = os.path.join(NEWS_DIR, f"{post_id}.html")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(pagina)


# =========================================================
# GERAR SITEMAP.XML
# =========================================================
today = date.today().isoformat()
sitemap_urls = [f"{BASE_URL}/", f"{BASE_URL}/index.html"]
sitemap_urls.extend(generated_news_urls)
sitemap_urls = list(dict.fromkeys(sitemap_urls))

sitemap_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
]
for url in sitemap_urls:
    sitemap_lines.extend([
        "  <url>",
        f"    <loc>{xml_escape(url)}</loc>",
        f"    <lastmod>{today}</lastmod>",
        "  </url>"
    ])
sitemap_lines.append("</urlset>")

with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(sitemap_lines))

print(f"{len(posts)} notícias geradas com sucesso!")
print(f"{len(generated_news_urls)} páginas adicionadas ao sitemap.xml!")
print(f"Sitemap atualizado: {SITEMAP_FILE}")
