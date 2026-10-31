#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURAÇÕES
# ==========================================

SITE = "https://pxngames.com"
URL_NOTICIAS = f"{SITE}/noticias"

ARQUIVO_PENDENTES = Path("noticias_pendentes.json")

LIMITE = 20

HEADERS = {
    "User-Agent": "CavaloGameNewsBot/1.0"
}

CATEGORIAS = {
    "Xbox": ["xbox"],
    "PlayStation": ["playstation", "ps5", "ps4", "psn", "ps plus"],
    "Nintendo": ["nintendo", "switch"],
    "PC": ["steam", "pc", "epic games", "epic games store"]
}

# Termos que ajudam a identificar notícias sobre games.
PALAVRAS_GAMES = [
    "game", "games", "jogo", "jogos", "gamer",
    "videogame", "videogames", "gaming",
    "xbox", "playstation", "nintendo", "switch",
    "ps5", "ps4", "steam", "pc", "ubisoft",
    "rockstar", "capcom", "sega", "konami",
    "square enix", "electronic arts", "ea sports",
    "activision", "blizzard", "bethesda",
    "epic games", "riot games", "valve",
    "playstation plus", "game pass",
    "dlc", "expansão", "update", "atualização",
    "lançamento", "jogabilidade", "desenvolvedora",
    "desenvolvimento", "estúdio", "servidores",
    "multiplayer", "single-player", "rpg",
    "shooter", "fps", "mmo", "console",
    "controle", "videogame"
]

# Expressões de conteúdos claramente fora do tema.
CONTEUDOS_FORA_DE_GAMES = [
    "o que você anda assistindo",
    "o que voce anda assistindo",
    "programação de tv",
    "programacao de tv",
    "novela",
    "reality show",
    "lançamento musical",
    "lancamento musical",
    "novo álbum",
    "novo album",
    "novo single",
    "clipe musical"
]


# ==========================================
# FUNÇÕES
# ==========================================

def carregar_pendentes():
    if not ARQUIVO_PENDENTES.exists():
        return []

    try:
        with ARQUIVO_PENDENTES.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return dados if isinstance(dados, list) else []

    except (json.JSONDecodeError, OSError) as erro:
        print(f"[ERRO] Não foi possível ler o arquivo: {erro}")
        raise


def salvar_pendentes(noticias):
    temporario = ARQUIVO_PENDENTES.with_suffix(".tmp")

    temporario.write_text(
        json.dumps(noticias, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    temporario.replace(ARQUIVO_PENDENTES)


def limpar_texto(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def normalizar_url(url):
    if not url:
        return ""

    # Remove fragmentos como #comentarios.
    url, _ = urldefrag(url)

    return url.rstrip("/")


def identificar_categoria(texto):
    texto = texto.lower()

    for categoria, palavras in CATEGORIAS.items():
        if any(palavra in texto for palavra in palavras):
            return categoria

    return "Notícias"


def eh_noticia_de_games(titulo, descricao):
    texto = f"{titulo} {descricao}".lower()

    # Descarta conteúdos claramente fora do tema.
    for palavra in CONTEUDOS_FORA_DE_GAMES:
        if palavra in texto:
            return False

    # Exige pelo menos um indicador relacionado a games.
    return any(palavra in texto for palavra in PALAVRAS_GAMES)


def remover_duplicadas(noticias):
    unicas = []
    encontrados = {}

    for noticia in noticias:
        if not isinstance(noticia, dict):
            continue

        link = normalizar_url(noticia.get("link_original", ""))
        identificador = noticia.get("id", "")

        chave = link or identificador

        if not chave:
            unicas.append(noticia)
            continue

        if chave not in encontrados:
            noticia["link_original"] = link
            encontrados[chave] = noticia
            unicas.append(noticia)
            continue

        existente = encontrados[chave]

        # Preserva uma aprovação ou rejeição já realizada.
        status_existente = existente.get("status", "pendente")
        status_novo = noticia.get("status", "pendente")

        if status_existente == "pendente" and status_novo != "pendente":
            existente["status"] = status_novo

        print(f"[DUPLICADA REMOVIDA] {noticia.get('titulo', chave)}")

    return unicas


def obter_pagina(url):
    resposta = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    resposta.raise_for_status()

    return BeautifulSoup(resposta.text, "html.parser")


def obter_descricao(soup):
    seletores = [
        'meta[property="og:description"]',
        'meta[name="description"]'
    ]

    for seletor in seletores:
        elemento = soup.select_one(seletor)

        if elemento and elemento.get("content"):
            return limpar_texto(elemento["content"])

    return ""


def obter_imagem(soup):
    elemento = soup.select_one('meta[property="og:image"]')

    if elemento:
        return elemento.get("content", "").strip()

    return ""


def obter_noticias_do_site():
    print("[INFO] Acessando PXN Games...")

    soup = obter_pagina(URL_NOTICIAS)

    links = []
    encontrados = set()

    for elemento in soup.select('a[href*="/noticia/"]'):
        url = urljoin(SITE, elemento.get("href", ""))
        url = normalizar_url(url)

        if not url:
            continue

        if url in encontrados:
            continue

        encontrados.add(url)
        links.append(url)

    print(f"[INFO] Encontrados {len(links)} links únicos.")

    return links[:LIMITE]


def extrair_noticia(url):
    soup = obter_pagina(url)

    titulo_elemento = soup.find("h1")

    if not titulo_elemento:
        return None

    titulo = limpar_texto(titulo_elemento.get_text())

    if not titulo:
        return None

    descricao = obter_descricao(soup)

    # Não adiciona conteúdos que não sejam notícias de games.
    if not eh_noticia_de_games(titulo, descricao):
        print(f"[IGNORADA] Conteúdo fora do tema: {titulo}")
        return None

    imagem = obter_imagem(soup)

    categoria = identificar_categoria(
        titulo + " " + descricao
    )

    slug = urlparse(url).path.rstrip("/").split("/")[-1]

    return {
        "id": slug,
        "titulo": titulo,
        "categoria": categoria,
        "fonte": "PXN Games",
        "link_original": url,
        "resumo": descricao,
        "imagem": imagem,
        "status": "pendente"
    }


# ==========================================
# EXECUÇÃO
# ==========================================

def main():
    pendentes = carregar_pendentes()

    # Limpa duplicadas que já estavam no arquivo.
    total_anterior = len(pendentes)
    pendentes = remover_duplicadas(pendentes)

    removidas = total_anterior - len(pendentes)

    if removidas:
        print(f"[INFO] Duplicadas antigas removidas: {removidas}")

    links_existentes = {
        normalizar_url(noticia.get("link_original", ""))
        for noticia in pendentes
        if isinstance(noticia, dict)
    }

    links = obter_noticias_do_site()

    novas = []

    for url in links:
        url = normalizar_url(url)

        if url in links_existentes:
            continue

        try:
            noticia = extrair_noticia(url)

            if noticia:
                novas.append(noticia)
                links_existentes.add(url)

                print(f"[NOVA PENDENTE] {noticia['titulo']}")

            time.sleep(1)

        except requests.RequestException as erro:
            print(f"[ERRO] Falha ao acessar {url}: {erro}")

        except Exception as erro:
            print(f"[ERRO] Problema ao processar notícia: {erro}")

    if novas:
        pendentes.extend(novas)

    # Salva também quando só houver duplicadas antigas para limpar.
    if novas or removidas:
        salvar_pendentes(pendentes)

    print("--------------------------------")
    print(f"[RESUMO] Duplicadas removidas: {removidas}")
    print(f"[RESUMO] Novas notícias: {len(novas)}")
    print(f"[RESUMO] Total no arquivo: {len(pendentes)}")
    print("--------------------------------")
    print("[INFO] Nenhuma notícia foi publicada no site.")


if __name__ == "__main__":
    main()
