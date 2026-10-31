#!/usr/bin/env python3

import json
import re
import time
import unicodedata
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
    "PlayStation": ["playstation", "ps5", "ps4", "ps plus", "psn"],
    "Nintendo": ["nintendo", "switch"],
    "PC": ["steam", "epic games", "pc"]
}

# Termos que indicam notícias relacionadas a games.
PALAVRAS_GAMES = [
    "jogo", "jogos", "game", "games", "gamer", "gaming",
    "videogame", "videogames", "xbox", "playstation",
    "nintendo", "switch", "ps5", "ps4", "ps plus",
    "steam", "epic games", "ubisoft", "rockstar",
    "resident evil", "gears of war", "prince of persia",
    "crimson desert", "john romero", "doom",
    "game pass", "shooter", "fps", "rpg", "dlc",
    "desenvolvedora", "desenvolvimento de jogos",
    "estúdio de jogos", "estudio de jogos",
    "jogabilidade", "multiplayer", "lançamento de jogo",
    "lançamento de jogos", "lançamento de games",
    "indie", "indies", "controle de videogame"
]

# Conteúdos que devem ser ignorados.
PALAVRAS_EXCLUIDAS = [
    "o que você anda assistindo",
    "o que voce anda assistindo",
    "seja série, filme",
    "seja serie, filme",
    "novo álbum",
    "novo album",
    "novo single",
    "clipe musical",
    "lançamento musical",
    "lancamento musical"
]


# ==========================================
# UTILITÁRIOS
# ==========================================

def normalizar_texto(texto):
    texto = (texto or "").lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()


def limpar_texto(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def normalizar_url(url):
    if not url:
        return ""

    url = urljoin(SITE, url)
    url, _ = urldefrag(url)

    partes = urlparse(url)

    return partes._replace(
        query="",
        fragment=""
    ).geturl().rstrip("/")


def carregar_pendentes():
    if not ARQUIVO_PENDENTES.exists():
        return []

    try:
        with ARQUIVO_PENDENTES.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if isinstance(dados, list):
            return dados

        print("[AVISO] O arquivo não contém uma lista.")
        return []

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


# ==========================================
# FILTRO E CATEGORIAS
# ==========================================

def eh_noticia_de_games(titulo, descricao):
    texto = normalizar_texto(f"{titulo} {descricao}")

    if any(
        normalizar_texto(palavra) in texto
        for palavra in PALAVRAS_EXCLUIDAS
    ):
        return False

    return any(
        normalizar_texto(palavra) in texto
        for palavra in PALAVRAS_GAMES
    )


def identificar_categoria(texto):
    texto = normalizar_texto(texto)

    # PlayStation
    if any(p in texto for p in [
        "playstation", "ps5", "ps4", "ps plus", "psn"
    ]):
        return "PlayStation"

    # Xbox
    if "xbox" in texto or "game pass" in texto:
        return "Xbox"

    # Nintendo
    if "nintendo" in texto or "switch" in texto:
        return "Nintendo"

    # PC
    if any(p in texto for p in [
        "steam", "epic games", "pc"
    ]):
        return "PC"

    return "Notícias"


# ==========================================
# ACESSO AO PXN GAMES
# ==========================================

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
        url = normalizar_url(elemento.get("href", ""))

        if not url:
            continue

        if url in encontrados:
            continue

        encontrados.add(url)
        links.append(url)

    print(f"[INFO] Encontrados {len(links)} links únicos.")

    return links[:LIMITE]


# ==========================================
# EXTRAÇÃO
# ==========================================

def extrair_noticia(url):
    soup = obter_pagina(url)

    titulo_elemento = soup.find("h1")

    if not titulo_elemento:
        return None

    titulo = limpar_texto(titulo_elemento.get_text())

    if not titulo:
        return None

    descricao = obter_descricao(soup)

    if not eh_noticia_de_games(titulo, descricao):
        print(f"[IGNORADA] Fora do tema: {titulo}")
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
        "link_original": normalizar_url(url),
        "resumo": descricao,
        "imagem": imagem,
        "status": "pendente"
    }


# ==========================================
# LIMPEZA DO ARQUIVO EXISTENTE
# ==========================================

def limpar_pendentes(noticias):
    unicas = []
    encontrados = {}

    duplicadas = 0
    fora_do_tema = 0
    categorias_corrigidas = 0

    for noticia in noticias:
        if not isinstance(noticia, dict):
            continue

        titulo = noticia.get("titulo", "")
        resumo = noticia.get("resumo", "")

        if not eh_noticia_de_games(titulo, resumo):
            print(f"[REMOVIDA] Fora do tema: {titulo}")
            fora_do_tema += 1
            continue

        link = normalizar_url(noticia.get("link_original", ""))
        identificador = noticia.get("id", "")

        chave = link or identificador

        noticia["link_original"] = link

        categoria_correta = identificar_categoria(
            titulo + " " + resumo
        )

        if noticia.get("categoria") != categoria_correta:
            noticia["categoria"] = categoria_correta
            categorias_corrigidas += 1

        if not chave:
            unicas.append(noticia)
            continue

        if chave in encontrados:
            existente = encontrados[chave]

            status_existente = existente.get("status", "pendente")
            status_novo = noticia.get("status", "pendente")

            if status_existente == "pendente" and status_novo != "pendente":
                existente["status"] = status_novo

            duplicadas += 1
            print(f"[DUPLICADA REMOVIDA] {titulo}")
            continue

        encontrados[chave] = noticia
        unicas.append(noticia)

    return unicas, duplicadas, fora_do_tema, categorias_corrigidas


# ==========================================
# EXECUÇÃO
# ==========================================

def main():
    print("================================")
    print(" CAVALOGAMENEWS - BUSCADOR PXN")
    print("================================")

    pendentes = carregar_pendentes()

    pendentes, duplicadas, fora_do_tema, categorias_corrigidas = (
        limpar_pendentes(pendentes)
    )

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

    pendentes.extend(novas)

    salvar_pendentes(pendentes)

    print("--------------------------------")
    print(f"[RESUMO] Duplicadas removidas: {duplicadas}")
    print(f"[RESUMO] Fora do tema removidas: {fora_do_tema}")
    print(f"[RESUMO] Categorias corrigidas: {categorias_corrigidas}")
    print(f"[RESUMO] Novas notícias: {len(novas)}")
    print(f"[RESUMO] Total no arquivo: {len(pendentes)}")
    print("--------------------------------")
    print("[INFO] Todas as notícias novas estão pendentes.")
    print("[INFO] O posts.json não foi alterado.")
    print("[INFO] Nenhuma publicação foi realizada.")


if __name__ == "__main__":
    main()
