import json
import os
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from playwright.sync_api import sync_playwright

ARQUIVO = "InstantGaming.json"
URL_OFERTAS = "https://www.instant-gaming.com/pt/tendencias/?currency=BRL"
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


def carregar_lista_anterior():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def ler_preco(texto):
    encontrados = re.findall(
        r"R\$\s*[\d.]+,\d{2}",
        texto.replace("\xa0", " ")
    )

    if not encontrados:
        return ""

    return encontrados[0]


def identificar_plataforma(texto):
    texto = texto.lower()

    if "nintendo switch 2" in texto:
        return "Nintendo Switch 2"
    elif "nintendo switch" in texto:
        return "Nintendo Switch"
    elif "playstation 5" in texto or "ps5" in texto:
        return "PlayStation 5"
    elif "playstation 4" in texto or "ps4" in texto:
        return "PlayStation 4"
    elif "xbox series" in texto:
        return "Xbox Series X|S"
    elif "xbox one" in texto:
        return "Xbox One"
    elif "ubisoft connect" in texto:
        return "PC (Ubisoft Connect)"
    elif "ea app" in texto or "ea play" in texto:
        return "PC (EA app)"
    elif "rockstar" in texto:
        return "PC (Rockstar)"
    elif "steam" in texto:
        return "PC (Steam)"
    elif "pc" in texto:
        return "PC"

    return "Plataforma não identificada"


def buscar_ofertas():
    ofertas = []
    vistos = set()

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        pagina = navegador.new_page(
            locale="pt-BR",
            viewport={"width": 1440, "height": 1000}
        )

        pagina.goto(
            URL_OFERTAS,
            wait_until="domcontentloaded",
            timeout=90000
        )

        pagina.wait_for_timeout(8000)

        # Rola a página para carregar mais jogos.
        for _ in range(6):
            pagina.mouse.wheel(0, 1800)
            pagina.wait_for_timeout(1500)

        cartoes = pagina.locator('a[href*="comprar-"]')
        quantidade = cartoes.count()

        print(f"Cartões encontrados na página: {quantidade}")

        for i in range(quantidade):
            link = cartoes.nth(i)

            try:
                url = link.get_attribute("href")

                if not url:
                    continue

                url = urljoin(URL_OFERTAS, url)

                if "instant-gaming.com" not in url:
                    continue

                imagem = link.locator("img").first

                if imagem.count() == 0:
                    continue

                nome = (
                    imagem.get_attribute("alt")
                    or link.get_attribute("title")
                    or ""
                ).strip()

                if not nome:
                    nome = link.inner_text().strip()

                if not nome:
                    continue

                nome_lower = nome.casefold()

                if nome_lower in vistos:
                    continue

                if nome_lower.startswith(("dlc ", "gift card")):
                    continue

                src = (
                    imagem.get_attribute("data-src")
                    or imagem.get_attribute("data-original")
                    or imagem.get_attribute("src")
                )

                if not src or src.startswith("data:"):
                    continue

                src = urljoin(URL_OFERTAS, src)

                texto = link.inner_text().strip()
                preco = ler_preco(texto)

                desconto_encontrado = re.search(
                    r"-\s*(\d{1,3})\s*%",
                    texto
                )

                if desconto_encontrado:
                    desconto = f"-{desconto_encontrado.group(1)}%"
                else:
                    desconto = "Sem desconto informado"

                ofertas.append({
                    "nome": nome,
                    "plataforma": identificar_plataforma(texto),
                    "imagem": src,
                    "preco": preco or "Preço não informado",
                    "desconto": desconto,
                    "url": adicionar_afiliado(url)
                })

                vistos.add(nome_lower)

                if len(ofertas) >= LIMITE:
                    break

            except Exception as erro:
                print(f"Cartão {i} ignorado: {erro}")

        navegador.close()

    return ofertas


def main():
    anteriores = carregar_lista_anterior()

    try:
        ofertas = buscar_ofertas()
    except Exception as erro:
        print(f"Falha ao consultar tendências: {erro}")
        raise SystemExit(1)

    # Proteção contra resultados vazios ou incompletos.
    if len(ofertas) < 5:
        print(
            f"Apenas {len(ofertas)} jogos encontrados. "
            "A lista anterior será preservada."
        )
        raise SystemExit(1)

    temporario = ARQUIVO + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(ofertas, arquivo, ensure_ascii=False, indent=2)

    os.replace(temporario, ARQUIVO)

    print(f"Tendências atualizadas: {len(ofertas)} jogos.")
    print(f"Lista anterior: {len(anteriores)} jogos.")
    print("Arquivo InstantGaming.json salvo com sucesso.")


if __name__ == "__main__":
    main()
