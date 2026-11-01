import json
import os
import re
import unicodedata
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from playwright.sync_api import sync_playwright

ARQUIVO = "InstantGaming.json"
URL_OFERTAS = "https://www.instant-gaming.com/pt/tendencias/?currency=BRL"
AFILIADO = "gamer-c0b7c0b"
LIMITE = 30
MINIMO_VALIDO = 5


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.casefold()


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
        (texto or "").replace("\xa0", " ")
    )

    return encontrados[0] if encontrados else "Preço não informado"


def ler_desconto(texto):
    encontrado = re.search(r"-\s*(\d{1,3})\s*%", texto or "")

    if not encontrado:
        return "Sem desconto informado"

    return f"-{encontrado.group(1)}%"


def regiao_permitida(texto):
    texto = normalizar(texto)

    regioes = [
        "global",
        "america latina",
        "latin america",
        "latam",
        "brasil",
        "brazil"
    ]

    return any(regiao in texto for regiao in regioes)


def identificar_plataforma(texto):
    texto = normalizar(texto)

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


def carregar_lista_anterior():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        return dados if isinstance(dados, list) else []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


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

        for _ in range(8):
            pagina.mouse.wheel(0, 1800)
            pagina.wait_for_timeout(1500)

        cartoes = pagina.locator('a[href*="comprar-"]')
        quantidade = cartoes.count()

        print(f"Cartões encontrados: {quantidade}")

        for i in range(quantidade):
            if len(ofertas) >= LIMITE:
                break

            try:
                link = cartoes.nth(i)

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
                    or link.inner_text()
                ).strip()

                if not nome:
                    continue

                nome_normalizado = normalizar(nome)

                if nome_normalizado in vistos:
                    continue

                if nome_normalizado.startswith(("dlc ", "gift card")):
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

                # Procura informações de região no cartão e nos elementos
                # próximos. Só aceita regiões explicitamente identificadas.
                informacoes = texto + " " + nome

                for seletor in [
                    "xpath=..",
                    "xpath=../..",
                    "xpath=../../.."
                ]:
                    try:
                        elemento = link.locator(seletor).first
                        informacoes += " " + elemento.inner_text(timeout=2000)
                    except Exception:
                        pass

                if not regiao_permitida(informacoes):
                    print(f"[REGIÃO NÃO CONFIRMADA] {nome}")
                    continue

                preco = ler_preco(informacoes)
                desconto = ler_desconto(informacoes)

                ofertas.append({
                    "nome": nome,
                    "plataforma": identificar_plataforma(informacoes),
                    "imagem": src,
                    "preco": preco,
                    "desconto": desconto,
                    "url": adicionar_afiliado(url)
                })

                vistos.add(nome_normalizado)

                print(f"[ADICIONADO] {nome}")

            except Exception as erro:
                print(f"[AVISO] Cartão {i} ignorado: {erro}")

        navegador.close()

    return ofertas


def main():
    anteriores = carregar_lista_anterior()

    try:
        ofertas = buscar_ofertas()

    except Exception as erro:
        print(f"Falha ao consultar tendências: {erro}")
        raise SystemExit(1)

    if len(ofertas) < MINIMO_VALIDO:
        print(
            f"Somente {len(ofertas)} jogos com região confirmada. "
            "A lista anterior será preservada."
        )
        raise SystemExit(1)

    temporario = ARQUIVO + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            ofertas,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporario, ARQUIVO)

    print("--------------------------------")
    print(f"Jogos atualizados: {len(ofertas)}")
    print(f"Jogos anteriores: {len(anteriores)}")
    print("InstantGaming.json atualizado!")
    print("--------------------------------")


if __name__ == "__main__":
    main()
