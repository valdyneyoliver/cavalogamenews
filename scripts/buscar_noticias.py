import json
import re
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ARQUIVO = Path("noticias_pendentes.json")
LIMITE = 20

FONTES = [
    "https://news.google.com/rss/search?q=games+Xbox+PlayStation+PC&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://news.google.com/rss/search?q=video+games+Nintendo+Steam&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://news.google.com/rss/search?q=games+lan%C3%A7amento+atualiza%C3%A7%C3%A3o&hl=pt-BR&gl=BR&ceid=BR:pt-419",
]

def carregar_pendentes():
    if not ARQUIVO.exists():
        return []

    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except json.JSONDecodeError:
        print("[ERRO] noticias_pendentes.json está inválido.")
        raise SystemExit(1)


def identificar_categoria(titulo):
    texto = titulo.lower()

    if "xbox" in texto:
        return "Xbox"
    if "playstation" in texto or "ps5" in texto or "ps4" in texto:
        return "PlayStation"
    if "nintendo" in texto or "switch" in texto:
        return "Nintendo"
    if "steam" in texto or "pc" in texto:
        return "PC"
    if "grátis" in texto or "gratuito" in texto or "free game" in texto:
        return "Jogos Grátis"

    return "Notícia"


def limpar_titulo(titulo):
    return re.sub(r"\s+", " ", titulo).strip()


def buscar_fonte(url):
    requisicao = Request(
        url,
        headers={"User-Agent": "CavaloGameNewsBot/1.0"}
    )

    with urlopen(requisicao, timeout=30) as resposta:
        conteudo = resposta.read()

    raiz = ET.fromstring(conteudo)
    noticias = []

    for item in raiz.findall(".//item"):
        titulo = limpar_titulo(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        descricao = item.findtext("description") or ""
        descricao = re.sub(r"<[^>]+>", " ", descricao)
        descricao = limpar_titulo(descricao)

        if not titulo or not link:
            continue

        identificador = hashlib.sha256(
            link.encode("utf-8")
        ).hexdigest()[:16]

        noticias.append({
            "id": identificador,
            "titulo": titulo,
            "categoria": identificar_categoria(titulo),
            "fonte": urlparse(link).netloc,
            "link_original": link,
            "resumo": descricao[:500],
            "status": "pendente"
        })

    return noticias


def main():
    pendentes = carregar_pendentes()
    links_existentes = {
        noticia.get("link_original")
        for noticia in pendentes
        if isinstance(noticia, dict)
    }

    novas = []

    for fonte in FONTES:
        try:
            resultados = buscar_fonte(fonte)

            for noticia in resultados:
                if noticia["link_original"] in links_existentes:
                    continue

                novas.append(noticia)
                links_existentes.add(noticia["link_original"])

        except (HTTPError, URLError, TimeoutError, ET.ParseError) as erro:
            print(f"[AVISO] Não foi possível consultar uma fonte: {erro}")

    pendentes.extend(novas)
    pendentes = pendentes[-LIMITE:]

    temporario = ARQUIVO.with_suffix(".tmp")

    temporario.write_text(
        json.dumps(pendentes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    temporario.replace(ARQUIVO)

    print(f"[RESULTADO] {len(novas)} notícia(s) nova(s) encontrada(s).")
    print(f"[PENDENTES] {len(pendentes)} notícia(s) aguardando revisão.")


if __name__ == "__main__":
    main()
