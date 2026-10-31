#!/usr/bin/env python3

import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# ARQUIVOS
# ==========================================

ARQUIVO_PENDENTES = Path("noticias_pendentes.json")
ARQUIVO_APROVADAS = Path("noticias_aprovadas.json")

FUSO_HORARIO = ZoneInfo("America/Fortaleza")


# ==========================================
# FUNÇÕES
# ==========================================

def carregar_json(caminho):
    if not caminho.exists():
        return []

    with caminho.open("r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    return dados if isinstance(dados, list) else []


def salvar_json(caminho, dados):
    temporario = caminho.with_suffix(".tmp")

    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    temporario.replace(caminho)


def gerar_data():
    return datetime.now(FUSO_HORARIO).strftime("%d/%m/%Y")


def criar_conteudo(noticia):
    titulo = noticia.get("titulo", "").strip()
    resumo = noticia.get("resumo", "").strip()
    fonte = noticia.get("fonte", "PXN Games")
    link = noticia.get("link_original", "").strip()

    conteudo = []

    if resumo:
        conteudo.append(resumo)

    conteudo.append("─────────────")
    conteudo.append("[verde]Leia a notícia completa[/verde]")

    if link:
        conteudo.append(
            f"[verde][Fonte: {fonte}]({link})[/verde]"
        )

    return conteudo


def converter_noticia(noticia):
    return {
        "id": noticia.get("id", ""),
        "titulo": noticia.get("titulo", "").strip(),
        "categoria": noticia.get("categoria", "Notícias"),
        "data": gerar_data(),
        "imagem": noticia.get("imagem", ""),
        "resumo": noticia.get("resumo", "").strip(),
        "conteudo": criar_conteudo(noticia)
    }


# ==========================================
# APROVAÇÃO
# ==========================================

def main():
    print("================================")
    print(" CAVALOGAMENEWS - APROVAR NOTÍCIAS")
    print("================================")

    pendentes = carregar_json(ARQUIVO_PENDENTES)
    aprovadas = carregar_json(ARQUIVO_APROVADAS)

    ids_existentes = {
        noticia.get("id")
        for noticia in aprovadas
        if isinstance(noticia, dict)
    }

    novas = []

    for noticia in pendentes:
        if not isinstance(noticia, dict):
            continue

        if noticia.get("status") != "aprovada":
            continue

        identificador = noticia.get("id", "")

        if not identificador:
            print("[IGNORADA] Notícia sem ID.")
            continue

        if identificador in ids_existentes:
            print(f"[JÁ EXISTE] {noticia.get('titulo', identificador)}")
            continue

        nova = converter_noticia(noticia)

        novas.append(nova)
        ids_existentes.add(identificador)

        print(f"[APROVADA] {nova['titulo']}")

    if novas:
        aprovadas.extend(novas)
        salvar_json(ARQUIVO_APROVADAS, aprovadas)

    print("--------------------------------")
    print(f"[RESUMO] Novas aprovadas: {len(novas)}")
    print(f"[RESUMO] Total em noticias_aprovadas.json: {len(aprovadas)}")
    print("--------------------------------")
    print("[INFO] posts.json não foi alterado.")
    print("[INFO] Nenhuma notícia foi publicada.")


if __name__ == "__main__":
    main()
