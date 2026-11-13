import json
import os
import html
import re
import random
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape as xml_escape

# =========================================================
# CONFIGURAÇÕES
# =========================================================
BASE_URL = "https://cavalogamenews.com.br"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_FILE = os.path.join(BASE_DIR, "posts.json")
NEWS_DIR = os.path.join(BASE_DIR, "noticias")
SITEMAP_FILE = os.path.join(BASE_DIR, "sitemap.xml")
LOGO_PATH = "../img/logo.png"
FAVICON_PATH = "../img/logo_cavalo.png"
PRODUCTS_FILE = os.path.join(BASE_DIR, "produtos.json")

# Produtos vêm do produtos.json (fonte única do catálogo).
try:
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        produtos_json = json.load(f)
    if not isinstance(produtos_json, list):
        raise ValueError("O arquivo produtos.json precisa conter uma lista de produtos.")
    PRODUTOS_AFILIADOS = [
        produto for produto in produtos_json
        if isinstance(produto, dict)
        and produto.get("nome")
        and produto.get("imagem")
        and produto.get("url")
    ]
except FileNotFoundError:
    print("Aviso: produtos.json não encontrado. As notícias serão geradas sem anúncio de produto.")
    PRODUTOS_AFILIADOS = []

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


def formatar_data_publicacao(data_hora):
    meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    return (
        f"Em {data_hora.day} de {meses[data_hora.month - 1]} de "
        f"{data_hora.year} às {data_hora:%H:%M}"
    )


def gerar_anuncio_produto(post):
    """Escolhe aleatoriamente um produto do produtos.json para a notícia nova."""
    if not PRODUTOS_AFILIADOS:
        return ""

    produto = random.choice(PRODUTOS_AFILIADOS)
    nome = html.escape(str(produto.get("nome", "Produto recomendado")))
    categoria = html.escape(str(produto.get("categoria", "Games")))
    descricao = html.escape(str(produto.get("descricao", "")))
    alt = html.escape(str(produto.get("alt", produto.get("nome", "Produto recomendado"))), quote=True)
    url = html.escape(str(produto["url"]), quote=True)

    imagem_arquivo = str(produto["imagem"]).strip()
    if imagem_arquivo.startswith(("https://", "http://")):
        imagem = html.escape(imagem_arquivo, quote=True)
    else:
        imagem = html.escape("../img/produtos/" + imagem_arquivo.lstrip("/"), quote=True)

    return f"""
<aside class="anuncio-produto" aria-label="Produto recomendado">
  <span class="anuncio-produto-label">🛒 PRODUTO RECOMENDADO</span>
  <div class="anuncio-produto-conteudo">
    <img src="{imagem}" alt="{alt}" loading="lazy">
    <div class="anuncio-produto-info">
      <span class="anuncio-produto-categoria">{categoria}</span>
      <h3>{nome}</h3>
      <p>{descricao}</p>
      <a class="anuncio-produto-botao" href="{url}" target="_blank"
         rel="sponsored nofollow noopener noreferrer">CONFERIR NA AMAZON</a>
      <small>Como associado da Amazon, o CavaloGameNews recebe por compras qualificadas.</small>
    </div>
  </div>
</aside>
"""


def renderizar_conteudo(post, incluir_anuncio=False):
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

        links_personalizados = []

        def guardar_link(match):
            nome = match.group(1)
            url = html.unescape(match.group(2))

            link = (
                f'<a href="{html.escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{nome}</a>'
            )

            marcador = f"MARCADORLINK{len(links_personalizados)}FIM"
            links_personalizados.append((marcador, link))
            return marcador

        texto = re.sub(
            r'\[([^\]]+)\]\((https?://[^\s)]+)\)',
            guardar_link,
            texto
        )

        texto = re.sub(
            r'(https?://[^\s<]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            texto
        )

        for marcador, link in links_personalizados:
            texto = texto.replace(marcador, link)

        conteudo_html += f"<p>{texto}</p>\n"

        if x_html and indice + 1 == meio:
            conteudo_html += x_html

    if x_html and len(validos) == 1:
        conteudo_html += x_html

    # Para não alterar notícias antigas, o anúncio só entra nas páginas novas.
    if incluir_anuncio:
        anuncio_html = gerar_anuncio_produto(post)
        if anuncio_html:
            primeiro_paragrafo = re.search(r"</p>\s*", conteudo_html, flags=re.IGNORECASE)
            if primeiro_paragrafo:
                posicao = primeiro_paragrafo.end()
                conteudo_html = conteudo_html[:posicao] + anuncio_html + conteudo_html[posicao:]
            else:
                conteudo_html += anuncio_html

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
    caminho = os.path.join(NEWS_DIR, f"{post_id}.html")
    pagina_existente = os.path.exists(caminho)
    incluir_anuncio = not pagina_existente
    conteudo_html = renderizar_conteudo(post, incluir_anuncio=incluir_anuncio)

    # Ao regenerar o site, preserva o produto que já estava nesta notícia.
    # Assim, publicar uma notícia nova não apaga os anúncios das notícias anteriores.
    if pagina_existente:
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo_existente:
                html_existente_produto = arquivo_existente.read()
            anuncio_existente = re.search(
                r'<aside class="anuncio-produto"\b.*?</aside>',
                html_existente_produto,
                flags=re.IGNORECASE | re.DOTALL
            )
            if 'class="anuncio-produto"' not in conteudo_html:
                # Preserva o anúncio antigo quando ele ainda existe no HTML.
                # Se já tiver sido apagado em uma execução anterior, recria um
                # anúncio usando o catálogo atual de produtos.json.
                if anuncio_existente:
                    bloco_anuncio = anuncio_existente.group(0)
                else:
                    bloco_anuncio = gerar_anuncio_produto(post)

                if bloco_anuncio:
                    primeiro_paragrafo = re.search(r"</p>\s*", conteudo_html, flags=re.IGNORECASE)
                    if primeiro_paragrafo:
                        posicao = primeiro_paragrafo.end()
                        conteudo_html = conteudo_html[:posicao] + "\n" + bloco_anuncio + "\n" + conteudo_html[posicao:]
                    else:
                        conteudo_html += "\n" + bloco_anuncio
        except (OSError, UnicodeError):
            pass

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
            related_resumo = str(related.get("resumo", "")).strip()
            related_imagem = str(related.get("imagem", ""))
            related_categoria = str(related.get("categoria", "Notícia"))
            related_data = str(related.get("data", "")).strip()
            related_views = related.get("visualizacoes", related.get("views", ""))
            resumo_curto = related_resumo if len(related_resumo) <= 105 else related_resumo[:102].rsplit(" ", 1)[0] + "..."
            categorias = [c.strip() for c in re.split(r"[,|/]", related_categoria) if c.strip()]
            categorias_html = "".join(
                f'<span class="related-tag">{html.escape(tag)}</span>' for tag in categorias[:2]
            )
            meta_partes = []
            if related_data:
                meta_partes.append(f'<span>{html.escape(related_data)}</span>')
            if related_views not in (None, ""):
                meta_partes.append(f'<span>◉ {html.escape(str(related_views))}</span>')
            meta_html = "<div class=\"related-meta\">" + "<span> · </span>".join(meta_partes) + "</div>" if meta_partes else ""
            autoria_humana = (
                '<span class="human-authorship">✓ Autoria humana</span>'
                if related.get("autoria_humana") is True else ""
            )
            resumo_html = f'<p class="related-summary">{html.escape(resumo_curto)}</p>' if resumo_curto else ""
            cards_html += f"""
<a href="../noticias/{escape_attr(related_id)}.html" class="related-card">
  <img class="related-image" src="{escape_attr(related_imagem)}" alt="{escape_attr(related_titulo)}" loading="lazy">
  <div class="related-content">
    <h3>{html.escape(related_titulo)}</h3>
    {resumo_html}
    <div class="related-tags">{categorias_html}</div>
    {meta_html}
    {autoria_humana}
  </div>
</a>
"""
        return cards_html

    related_html = montar_cards(relacionadas_lateral)
    more_html = montar_cards(relacionadas_mais)

    # Mantém a autoria e a data/hora quando a notícia já foi gerada.

    metadados_antigos = ""
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo_existente:
                html_antigo = arquivo_existente.read()

            inicio = html_antigo.find('<div class="info autor">')
            fim = html_antigo.find("</div>", inicio)

            if inicio != -1 and fim != -1:
                fim += len("</div>")
                metadados_antigos = html_antigo[inicio:fim]

                inicio_data = html_antigo.find(
                    '<div class="info data-publicacao">',
                    fim
                )

                if inicio_data != -1:
                    fim_data = html_antigo.find("</div>", inicio_data)
                    if fim_data != -1:
                        fim_data += len("</div>")
                        metadados_antigos += "\n" + html_antigo[inicio_data:fim_data]

        except (OSError, UnicodeError):
            metadados_antigos = ""

    if metadados_antigos:
        metadados_noticia_html = metadados_antigos
    elif os.path.exists(caminho):
        metadados_noticia_html = f'<div class="info">{data} · CavaloGameNews</div>'
    else:
        data_hora_publicacao = datetime.now(ZoneInfo("America/Fortaleza"))
        data_publicacao_formatada = formatar_data_publicacao(data_hora_publicacao)

        metadados_noticia_html = f"""
        <div class="info autor">Por Valdiney Oliver</div>
        <div class="info data-publicacao">{html.escape(data_publicacao_formatada)}</div>
        """

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
  padding-top: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.6;
  transition: background .2s ease, color .2s ease;
}}
a {{ color: inherit; }}

.site-header {{
  position: sticky; top: 0; z-index: 1000; width: 100%;
  padding: 14px 24px 16px;
  background: rgba(5, 9, 7, .97);
  border-bottom: 1px solid rgba(0,232,135,.22);
  box-shadow: 0 8px 28px rgba(0,0,0,.22);
  backdrop-filter: blur(16px);
  transition: padding .3s ease;
}}
.header-inner {{
  position: relative; max-width: 1500px; margin: 0 auto;
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  transition: padding .3s ease, height .3s ease, opacity .25s ease, transform .3s ease;
}}
.brand {{ display: inline-flex; align-items: center; justify-content: center; text-decoration: none; min-height: 58px; transition: opacity .22s ease, transform .22s ease; }}
.brand img {{ display: block; width: auto; height: 54px; max-width: min(70vw, 360px); object-fit: contain; margin: 2px auto 0; transition: height .3s ease, opacity .25s ease, transform .3s ease; }}
.header-tools {{
  position: absolute; top: 7px; right: 0; display: flex; align-items: center;
  gap: 9px; z-index: 20; transition: opacity .25s ease, transform .3s ease;
}}
.theme-toggle {{
  width: 42px; height: 42px; display: inline-flex; align-items: center;
  justify-content: center; border: 1px solid rgba(0,232,135,.42);
  border-radius: 12px; background: #101914; color: #fff; cursor: pointer;
  font-size: 17px; transition: background .2s ease, border-color .2s ease, transform .2s ease;
}}
.theme-toggle:hover {{ background: #173323; border-color: #00e887; transform: translateY(-2px); }}
.article-nav {{
  width: 100%; min-height: 52px; box-sizing: border-box; display: flex;
  align-items: center; justify-content: center; flex-wrap: wrap;
  gap: 8px clamp(12px, 1.65vw, 25px); padding: 13px 18px;
  border: 1px solid rgba(0,232,135,.42); border-radius: 9px;
  background: linear-gradient(100deg, #06351f 0%, #087b43 48%, #00a95f 100%);
  box-shadow: 0 7px 22px rgba(0,180,100,.16);
}}
.article-nav a, .article-nav button {{
  color: #fff; font-size: 13px; font-weight: 800; letter-spacing: .025em;
  text-decoration: none; white-space: nowrap; transition: opacity .2s ease, transform .2s ease;
}}
.article-nav a:hover {{ color: #fff; opacity: .78; transform: translateY(-1px); }}
.article-nav .support-button {{
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 0; margin: 0; padding: 0; border: 0; border-radius: 0;
  background: transparent; color: #fff; font: inherit; cursor: pointer;
}}
.article-nav .support-button:hover {{ color: #fff; opacity: .78; transform: translateY(-1px); }}
.article-nav .live-button {{ color: #fff; }}
body[data-theme="light"] .site-header {{ background: rgba(248,251,249,.98); border-color: #dce7df; }}
body[data-theme="light"] .theme-toggle {{
  background: #fff; color: #24352a; border-color: #cbded1;
}}
.site-header, .site-header .brand img, .site-header .header-tools, .site-header .article-nav {{
  transition: padding .3s ease, height .3s ease, opacity .25s ease, transform .3s ease;
}}
.site-header.header-compact {{ padding: 4px 24px; }}
.site-header.header-compact .header-inner {{ height: 40px; min-height: 40px; gap: 0; }}
.site-header.header-compact .brand {{ position: absolute; top: 0; left: 50%; opacity: 0; transform: translate(-50%, -12px); pointer-events: none; }}
.site-header.header-compact .header-tools {{ opacity: 0; transform: translateY(-12px); pointer-events: none; }}
.site-header.header-compact .article-nav {{ min-height: 40px; padding-top: 8px; padding-bottom: 8px; transform: none; }}
@media (max-width: 900px) {{
  .site-header {{ padding: 12px 12px 14px; }}
  .site-header .header-inner {{ flex-direction: column; align-items: center; gap: 13px; }}
  .site-header .brand img {{ height: 46px; max-width: 65vw; margin: 3px auto 0; }}
  .site-header .header-tools {{ position: absolute; top: 2px; right: 0; }}
  .site-header .theme-toggle {{ width: 38px; height: 38px; }}
  .article-nav {{ justify-content: flex-start; flex-wrap: nowrap; gap: 10px; overflow-x: auto; overflow-y: hidden; white-space: nowrap; }}
  .article-nav a {{ font-size: 11px; }}
  .site-header.header-compact {{ padding: 4px 12px; }}
}}
@media (max-width: 560px) {{
  .site-header {{ padding: 12px 12px 14px; }}
  .site-header .brand img {{ height: 46px; max-width: 65vw; }}
  .article-nav {{ gap: 10px 14px; padding: 12px 10px; }}
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
.sidebar-card .related-card {{
  display: block;
  padding: 0;
  overflow: hidden;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 11px;
  color: var(--text);
  text-decoration: none;
  transition: transform .18s ease, border-color .18s ease;
}}
.sidebar-card .related-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
.sidebar-card .related-image {{
  display: block;
  width: 100%;
  height: 145px;
  object-fit: cover;
  border-radius: 0;
  background: var(--border);
}}
.sidebar-card .related-content {{ min-width: 0; padding: 10px 11px 11px; }}
.sidebar-card .related-content h3 {{ font-size: 14px; line-height: 1.3; margin: 0 0 7px; overflow-wrap: anywhere; }}
.related-summary {{ color: var(--muted); font-size: 12px; line-height: 1.45; margin: 0 0 9px; }}
.related-tags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }}
.related-tag {{ padding: 2px 6px; border-radius: 4px; background: var(--accent); color: #06140d; font-size: 9px; line-height: 1.5; font-weight: 800; text-transform: uppercase; }}
.related-meta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 3px; color: var(--muted); font-size: 10px; line-height: 1.4; }}
.human-authorship {{ display: block; margin-top: 5px; color: var(--accent); font-size: 10px; font-weight: 700; }}
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
  .site-header {{ padding: 8px 12px 0; }}
  .header-inner {{ grid-template-columns: minmax(0, 1fr) auto; column-gap: 10px; }}
  .brand {{ min-height: 44px; }}
  .brand img {{ height: 38px; max-width: 72vw; }}
  .article-nav {{ justify-content: flex-start; gap: 10px 14px; padding: 9px 10px; }}
  .article-nav a {{ font-size: 11px; }}
  .site-header.compact {{ padding: 4px 8px 0; }}
  .site-header.compact .article-nav {{ justify-content: center; gap: 8px 12px; padding: 8px; }}
  .page-wrap {{ margin-top: 22px; }}
  .layout {{ grid-template-columns: minmax(0, 1fr); }}
  .sidebar-card {{ position: static; }}
  .related-list {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .sidebar-card .related-image {{ height: 115px; }}
  .sidebar-card .related-content h3 {{ font-size: 13px; }}
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
  .sidebar-card .related-image {{ height: 160px; }}
  .more-news .related-grid {{ grid-template-columns: minmax(0, 1fr); }}
  .more-news .related-card {{ display: grid; grid-template-columns: 105px minmax(0, 1fr); }}
  .more-news .related-card img {{ width: 105px; height: 88px; }}

}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ scroll-behavior: auto !important; transition: none !important; }}
}}
.anuncio-produto {{
  margin: 28px 0;
  padding: 18px;
  border: 1px solid var(--accent);
  border-radius: 14px;
  background: var(--surface-2);
  overflow: hidden;
}}
.anuncio-produto-label {{
  display: inline-block;
  margin-bottom: 12px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .06em;
}}
.anuncio-produto-conteudo {{
  display: grid;
  grid-template-columns: minmax(110px, 180px) minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}}
.anuncio-produto-conteudo > img {{
  display: block;
  width: 100%;
  max-height: 190px;
  object-fit: contain;
  padding: 10px;
  border-radius: 10px;
  background: #fff;
}}
.anuncio-produto-categoria {{ color: var(--accent); font-size: 11px; font-weight: 800; }}
.anuncio-produto-info h3 {{ margin: 5px 0 8px; font-size: 19px; line-height: 1.35; }}
.anuncio-produto-info p {{ margin: 0 0 12px; color: var(--muted); font-size: 14px; line-height: 1.55; }}
.anuncio-produto-botao {{
  display: inline-block;
  padding: 11px 14px;
  border-radius: 8px;
  background: var(--accent);
  color: #06140d;
  font-size: 12px;
  font-weight: 800;
  text-decoration: none;
}}
.anuncio-produto-botao:hover {{ filter: brightness(.92); }}
.anuncio-produto-info small {{ display: block; margin-top: 10px; color: var(--muted); font-size: 10px; line-height: 1.5; }}
@media (max-width: 480px) {{
  .anuncio-produto {{ padding: 13px; }}
  .anuncio-produto-conteudo {{ grid-template-columns: minmax(0, 1fr); gap: 12px; }}
  .anuncio-produto-conteudo > img {{ max-height: 150px; }}
  .anuncio-produto-info h3 {{ font-size: 17px; }}
  .anuncio-produto-botao {{ display: block; text-align: center; }}
}}
</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="../index.html" aria-label="CavaloGameNews - página inicial">
      <img src="{LOGO_PATH}" alt="CavaloGameNews">
    </a>
    <div class="header-tools">
      <button class="theme-toggle" id="themeToggle" type="button" aria-label="Alternar tema" title="Alternar entre tema claro e escuro">☀️</button>
    </div>
    <nav class="article-nav" aria-label="Navegação principal">
      <a href="../index.html">INÍCIO</a>
      <a href="../index.html?categoria=Notícias">NOTÍCIAS</a>
      <a href="../index.html?categoria=Xbox">XBOX</a>
      <a href="../index.html?categoria=PlayStation">PLAYSTATION</a>
      <a href="../index.html?categoria=PC">PC</a>
      <a href="../index.html?categoria=Nintendo">NINTENDO</a>
      <a href="../index.html?categoria=Jogos%20Gr%C3%A1tis">JOGOS GRÁTIS</a>
      <a href="../ao-vivo.html" class="live-button">TRANSMITIR A TELA</a>
      <button class="support-button" id="supportButton" type="button">💚 APOIE</button>
    </nav>
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
        {metadados_noticia_html}
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

<footer>
    © 2026 CavaloGameNews — Todos os direitos reservados. |
    <a href="../politica-de-privacidade.html">Política de Privacidade</a>
</footer>

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

<script>
(function() {{
  const themeToggle = document.getElementById('themeToggle');
  const themeMeta = document.querySelector('meta[name="theme-color"]');

  function aplicarTema(modo, salvar = true) {{
    const tema = modo === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', tema);

    if (themeToggle) {{
      themeToggle.textContent = tema === 'light' ? '🌙' : '☀️';
      themeToggle.title = tema === 'light'
        ? 'Mudar para tema escuro'
        : 'Mudar para tema claro';
      themeToggle.setAttribute('aria-label', themeToggle.title);
    }}

    if (themeMeta) {{
      themeMeta.setAttribute('content', tema === 'light' ? '#f2f5f7' : '#0b0f14');
    }}

    if (salvar) {{
      try {{
        localStorage.setItem('tema-cavalogamenews', tema === 'light' ? 'claro' : 'escuro');
      }} catch (error) {{}}
    }}
  }}

  let temaSalvo = 'escuro';
  try {{
    temaSalvo = localStorage.getItem('tema-cavalogamenews') || 'escuro';
  }} catch (error) {{}}

  aplicarTema(temaSalvo === 'claro' ? 'light' : 'dark', false);

  if (themeToggle) {{
    themeToggle.addEventListener('click', function() {{
      const temaAtual = document.documentElement.getAttribute('data-theme');
      aplicarTema(temaAtual === 'light' ? 'dark' : 'light');
    }});
  }}
}})();
</script>

<script>
(function() {{
  const header = document.querySelector('.site-header');
  if (!header) return;
  let compacto = false;
  let quadroPendente = false;
  const atualizar = () => {{
    const posicao = window.scrollY || document.documentElement.scrollTop;
    if (!compacto && posicao > 130) compacto = true;
    else if (compacto && posicao < 55) compacto = false;
    header.classList.toggle('header-compact', compacto);
    quadroPendente = false;
  }};
  atualizar();
  window.addEventListener('scroll', () => {{
    if (quadroPendente) return;
    quadroPendente = true;
    requestAnimationFrame(atualizar);
  }}, {{ passive: true }});
}})();
</script>


<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body>
</html>
"""

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
