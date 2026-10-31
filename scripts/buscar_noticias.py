#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

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
    "xbox": ["xbox"],
    "playstation": ["playstation", "ps5", "ps4"],
    "nintendo": ["nintendo", "switch"],
    "pc": ["pc", "steam"],
}


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


def identificar_categoria(texto):
    texto = texto.lower()

    for categoria, palavras in CATEGORIAS.items():
        if any(palavra in texto for palavra in palavras):
            return categoria.capitalize()

    return "Notícia"


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

    for link in soup.select('a[href*="/noticia/"]'):
        url = urljoin(SITE, link.get("href", ""))

        if url in encontrados:
            continue

        encontrados.add(url)
        links.append(url)

    print(f"[INFO] Encontrados {len(links)} links de notícias.")

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

    links_existentes = {
        noticia.get("link_original")
        for noticia in pendentes
        if isinstance(noticia, dict)
    }

    links = obter_noticias_do_site()

    novas = []

    for url in links:
        if url in links_existentes:
            continue

        try:
            noticia = extrair_noticia(url)

            if noticia:
                novas.append(noticia)

                print(f"[NOVA] {noticia['titulo']}")

            time.sleep(1)

        except requests.RequestException as erro:
            print(f"[ERRO] Falha ao acessar {url}: {erro}")

        except Exception as erro:
            print(f"[ERRO] Problema ao processar notícia: {erro}")

    if novas:
        pendentes.extend(novas)
        salvar_pendentes(pendentes)

    print("--------------------------------")
    print(f"[RESUMO] Novas notícias: {len(novas)}")
    print(f"[RESUMO] Total pendente: {len(pendentes)}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
