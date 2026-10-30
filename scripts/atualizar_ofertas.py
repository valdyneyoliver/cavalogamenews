import json
import re
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

ARQUIVO = "InstantGaming.json"
URL_OFERTAS = "https://www.instant-gaming.com/pt/ofertas-do-dia/?currency=BRL"
AFILIADO = "gamer-c0b7c0b"
LIMITE = 30


def adicionar_afiliado(url):
    partes = urlparse(url)
    parametros = parse_qs(partes.query)
    parametros["igr"] = [AFILIADO]

    return urlunparse((
        partes.scheme,
        partes.netloc,
        partes.path,
        partes.params,
        urlencode(parametros, doseq=True),
        partes.fragment
    ))


def ler_preco(texto):
    encontrados = re.findall(
        r"R\$\s*[\d.]+,\d{2}",
        texto.replace("\xa0", " ")
    )

    if not encontrados:
        return None

    valor = encontrados[0]
    numero = float(
        valor.replace("R$", "").strip().replace(".", "").replace(",", ".")
    )

    return valor, numero


def ler_desconto(texto):
    encontrados = re.findall(r"-\s*(\d{1,3})\s*%", texto)

    if not encontrados:
        return None

    return int(encontrados[0])


def carregar_lista_anterior():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return dados if isinstance(dados, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def buscar_ofertas():
    resposta = requests.get(
        URL_OFERTAS,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9"
        },
        timeout=30
    )
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")
    ofertas = []
    vistos = set()

    for link in soup.find_all("a", href=True):
        url = link["href"]

        if "instant-gaming.com" not in url:
            continue

        if "comprar-" not in url:
            continue

        imagem = link.find("img")

        if imagem is None:
            imagem = None
            for pai in link.parents:
                imagem = pai.find("img")
                if imagem:
                    break
                if pai.name in ("body", "html"):
                    break

        if not imagem:
            continue

        nome = (
            imagem.get("alt")
            or link.get("title")
            or link.get_text(" ", strip=True)
        ).strip()

        if not nome or nome.casefold() in vistos:
            continue

        if nome.casefold().startswith("dlc "):
            continue

        if nome.casefold().startswith("gift card"):
            continue

        # Procura preço e desconto no cartão do jogo.
        texto_cartao = ""
        for pai in link.parents:
            texto = pai.get_text(" ", strip=True)
            if ler_preco(texto) and ler_desconto(texto):
                texto_cartao = texto
                break
            if pai.name in ("body", "html"):
                break

        preco = ler_preco(texto_cartao)
        desconto = ler_desconto(texto_cartao)

        if not preco or desconto is None:
            continue

        if not 0 <= desconto <= 100:
            continue

        src = (
            imagem.get("data-src")
            or imagem.get("data-original")
            or imagem.get("src")
        )

        if not src or src.startswith("data:"):
            continue

        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.instant-gaming.com" + src

        texto_plataforma = texto_cartao.lower()

        if "nintendo switch 2" in texto_plataforma:
            plataforma = "Nintendo Switch 2"
        elif "nintendo switch" in texto_plataforma:
            plataforma = "Nintendo Switch"
        elif "playstation 5" in texto_plataforma or "ps5" in texto_plataforma:
            plataforma = "PlayStation 5"
        elif "playstation 4" in texto_plataforma or "ps4" in texto_plataforma:
            plataforma = "PlayStation 4"
        elif "xbox series x|s" in texto_plataforma or "xbox series x" in texto_plataforma or "xbox series s" in texto_plataforma:
            plataforma = "Xbox Series X|S"
        elif "xbox one" in texto_plataforma:
            plataforma = "Xbox One"
        elif "ubisoft connect" in texto_plataforma:
            plataforma = "PC (Ubisoft Connect)"
        elif "ea app" in texto_plataforma or "ea play" in texto_plataforma:
            plataforma = "PC (EA app)"
        elif "rockstar" in texto_plataforma:
            plataforma = "PC (Rockstar)"
        elif "steam" in texto_plataforma:
            plataforma = "PC (Steam)"
        elif "pc" in texto_plataforma:
            plataforma = "PC"
        else:
            plataforma = "Plataforma não identificada"

        ofertas.append({
            "nome": nome,
            "plataforma": plataforma,
            "imagem": src,
            "preco": preco[0],
            "desconto": f"-{desconto}%",
            "url": adicionar_afiliado(url),
            "_valor": preco[1],
            "_desconto": desconto
        })

        vistos.add(nome.casefold())

    # Prioriza descontos altos e, em caso de empate, preços baixos.
    ofertas.sort(
        key=lambda jogo: (
            -jogo["_desconto"],
            jogo["_valor"]
        )
    )

    return ofertas[:LIMITE]


def main():
    anteriores = carregar_lista_anterior()

    try:
        ofertas = buscar_ofertas()
    except Exception as erro:
        print(f"Falha ao consultar ofertas: {erro}")
        raise SystemExit(1)

    # Evita apagar a lista se o site mudar de estrutura ou bloquear a consulta.
    if len(ofertas) < 5:
        print(
            f"Somente {len(ofertas)} ofertas válidas encontradas. "
            "A lista atual será preservada."
        )
        raise SystemExit(1)

    resultado = [
        {
            "nome": jogo["nome"],
            "plataforma": jogo["plataforma"],
            "imagem": jogo["imagem"],
            "preco": jogo["preco"],
            "desconto": jogo["desconto"],
            "url": jogo["url"]
        }
        for jogo in ofertas
    ]

    temporario = ARQUIVO + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(resultado, arquivo, ensure_ascii=False, indent=2)

    os.replace(temporario, ARQUIVO)

    print(f"Ofertas atualizadas: {len(resultado)} jogos.")
    print(f"Lista anterior: {len(anteriores)} jogos.")


if __name__ == "__main__":
    main()
