import json
import os
import html

BASE_URL = "https://valdyneyoliver.github.io/cavalogamenews"

with open("posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

os.makedirs("noticias", exist_ok=True)

for post in posts:
    post_id = post["id"]

    titulo = html.escape(post.get("titulo", "CavaloGameNews"))
    resumo = html.escape(post.get("resumo", ""))
    imagem = html.escape(post.get("imagem", ""))
    categoria = html.escape(post.get("categoria", "Notícias"))
    data = html.escape(post.get("data", ""))

    url = f"{BASE_URL}/noticias/{post_id}.html"

    paragrafos = post.get("conteudo", [post.get("resumo", "")])

    conteudo_html = ""

    for paragrafo in paragrafos:
        conteudo_html += f"<p>{html.escape(paragrafo)}</p>"

    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>{titulo} - CavaloGameNews</title>

<meta name="description" content="{resumo}">

<meta property="og:type" content="article">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{resumo}">
<meta property="og:image" content="{imagem}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="CavaloGameNews">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{titulo}">
<meta name="twitter:description" content="{resumo}">
<meta name="twitter:image" content="{imagem}">

<style>

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

.cover {{
    width: 100%;
    max-height: 560px;
    object-fit: cover;
    border-radius: 14px;
    display: block;
    margin-bottom: 30px;
}}

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

footer {{
    background: #1a1a1a;
    text-align: center;
    padding: 25px;
    margin-top: 50px;
    color: #888;
}}

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
<a href="../index.html">← Voltar para o CavaloGameNews</a>
</header>

<main class="article">

<div class="category">{categoria}</div>

<h1>{titulo}</h1>

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

<a class="back-button" href="../index.html">
← Voltar para as notícias
</a>

</div>

</main>

<footer>
© 2026 CavaloGameNews - Todos os direitos reservados.
</footer>

</body>
</html>
"""

    caminho = f"noticias/{post_id}.html"

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(pagina)

print(f"{len(posts)} notícias geradas com sucesso!")
