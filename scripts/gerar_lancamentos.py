import json
import os
import sys
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# =========================================================
# CONFIGURAÇÕES
# =========================================================

BASE_URL = "https://api.rawg.io/api/games"

OUTPUT_FILE = "lancamentos.json"

# Quantos dias à frente serão pesquisados
DIAS_FUTUROS = 120

# Quantos jogos serão exibidos no JSON
LIMITE_JOGOS = 100


# =========================================================
# PLATAFORMAS
# =========================================================
#
# IDs de parent platforms usados pela RAWG:
#
# 1  = PC
# 2  = PlayStation
# 3  = Xbox
# 7  = Nintendo
#
# A API da RAWG também retorna as plataformas individuais
# dentro de cada jogo.
# =========================================================

PLATAFORMAS = {
    "pc": {
        "parent_id": 1,
        "nome": "PC"
    },

    "playstation": {
        "parent_id": 2,
        "nome": "PlayStation"
    },

    "xbox": {
        "parent_id": 3,
        "nome": "Xbox"
    },

    "switch": {
        "parent_id": 7,
        "nome": "Switch"
    }
}


# =========================================================
# PEGAR API KEY
# =========================================================

API_KEY = os.environ.get("RAWG_API_KEY", "").strip()

if not API_KEY:
    print("ERRO: a variável RAWG_API_KEY não foi encontrada.")
    print()
    print("No GitHub Actions, verifique se o Secret está configurado")
    print("com o nome exatamente:")
    print()
    print("RAWG_API_KEY")
    print()

    sys.exit(1)


# =========================================================
# FUNÇÃO PARA CONSULTAR A RAWG
# =========================================================

def consultar_rawg(params):

    params = dict(params)

    params["key"] = API_KEY

    url = (
        BASE_URL
        + "?"
        + urlencode(params)
    )

    print()
    print("Consultando RAWG...")
    print(url.replace(API_KEY, "***"))

    request = Request(
        url,
        headers={
            "User-Agent": "CavaloGameNews/1.0"
        }
    )

    try:

        with urlopen(
            request,
            timeout=30
        ) as response:

            data = response.read().decode(
                "utf-8"
            )

            return json.loads(data)

    except HTTPError as erro:

        print(
            f"ERRO HTTP da RAWG: {erro.code}"
        )

        try:

            detalhe = erro.read().decode(
                "utf-8",
                errors="ignore"
            )

            print(detalhe)

        except Exception:
            pass

        sys.exit(1)

    except URLError as erro:

        print(
            "ERRO de conexão com a RAWG:"
        )

        print(erro)

        sys.exit(1)

    except Exception as erro:

        print(
            "ERRO ao consultar a RAWG:"
        )

        print(erro)

        sys.exit(1)


# =========================================================
# IDENTIFICAR PLATAFORMAS
# =========================================================

def identificar_plataformas(game):

    plataformas_encontradas = []

    plataformas = game.get(
        "platforms",
        []
    )

    if not isinstance(
        plataformas,
        list
    ):
        return plataformas_encontradas

    nomes = []

    for item in plataformas:

        if not isinstance(
            item,
            dict
        ):
            continue

        plataforma = item.get(
            "platform",
            {}
        )

        if not isinstance(
            plataforma,
            dict
        ):
            continue

        nome = str(
            plataforma.get(
                "name",
                ""
            )
        ).strip()

        slug = str(
            plataforma.get(
                "slug",
                ""
            )
        ).strip().lower()

        if nome:
            nomes.append(nome)

        # PC
        if (
            slug == "pc"
            or "windows" in slug
            or nome.lower() == "pc"
        ):

            if "PC" not in plataformas_encontradas:
                plataformas_encontradas.append(
                    "PC"
                )

        # PlayStation
        if (
            "playstation" in slug
            or "playstation" in nome.lower()
        ):

            if "PlayStation" not in plataformas_encontradas:
                plataformas_encontradas.append(
                    "PlayStation"
                )

        # Xbox
        if (
            "xbox" in slug
            or "xbox" in nome.lower()
        ):

            if "Xbox" not in plataformas_encontradas:
                plataformas_encontradas.append(
                    "Xbox"
                )

        # Switch
        if (
            "nintendo-switch" in slug
            or slug == "switch"
            or "switch" in nome.lower()
        ):

            if "Switch" not in plataformas_encontradas:
                plataformas_encontradas.append(
                    "Switch"
                )

    return plataformas_encontradas


# =========================================================
# CONVERTER DATA
# =========================================================

def formatar_data(data_iso):

    if not data_iso:
        return ""

    try:

        partes = data_iso.split("-")

        if len(partes) != 3:
            return data_iso

        ano = partes[0]
        mes = partes[1]
        dia = partes[2]

        return f"{dia}/{mes}/{ano}"

    except Exception:

        return data_iso


# =========================================================
# LIMPAR NOME DO JOGO
# =========================================================

def limpar_nome(nome):

    if not nome:
        return ""

    return (
        str(nome)
        .replace("\n", " ")
        .strip()
    )


# =========================================================
# CRIAR ITEM DO JOGO
# =========================================================

def criar_item(game):

    nome = limpar_nome(
        game.get(
            "name",
            ""
        )
    )

    released = str(
        game.get(
            "released",
            ""
        )
    ).strip()

    imagem = str(
        game.get(
            "background_image",
            ""
        )
    ).strip()

    slug = str(
        game.get(
            "slug",
            ""
        )
    ).strip()

    game_id = game.get(
        "id"
    )

    plataformas = identificar_plataformas(
        game
    )

    return {

        "id": game_id,

        "nome": nome,

        "slug": slug,

        "data": released,

        "data_formatada": formatar_data(
            released
        ),

        "imagem": imagem,

        "plataformas": plataformas,

        "link_rawg": (
            f"https://rawg.io/games/{slug}"
            if slug
            else ""
        )
    }


# =========================================================
# BUSCAR LANÇAMENTOS
# =========================================================

def buscar_lancamentos():

    hoje = date.today()

    fim = (
        hoje
        + timedelta(
            days=DIAS_FUTUROS
        )
    )

    data_inicio = hoje.isoformat()

    data_fim = fim.isoformat()

    print()
    print(
        "Período pesquisado:"
    )

    print(
        f"{data_inicio} até {data_fim}"
    )

    params = {

        "dates":
            f"{data_inicio},{data_fim}",

        "ordering":
            "released",

        "page_size":
            100
    }

    data = consultar_rawg(
        params
    )

    resultados = data.get(
        "results",
        []
    )

    if not isinstance(
        resultados,
        list
    ):

        resultados = []

    jogos = []

    for game in resultados:

        if not isinstance(
            game,
            dict
        ):
            continue

        item = criar_item(
            game
        )

        # Ignora jogos sem nome
        if not item["nome"]:
            continue

        # Ignora jogos sem data
        if not item["data"]:
            continue

        # Ignora jogos sem imagem
        if not item["imagem"]:
            continue

        # Só adiciona jogos que tenham
        # pelo menos uma das plataformas
        # que queremos mostrar.
        if not item["plataformas"]:
            continue

        jogos.append(
            item
        )

    return jogos


# =========================================================
# REMOVER DUPLICADOS
# =========================================================

def remover_duplicados(jogos):

    resultado = []

    ids = set()

    for jogo in jogos:

        game_id = jogo.get(
            "id"
        )

        if game_id in ids:
            continue

        ids.add(
            game_id
        )

        resultado.append(
            jogo
        )

    return resultado


# =========================================================
# ORDENAR
# =========================================================

def ordenar_jogos(jogos):

    return sorted(
        jogos,
        key=lambda jogo: (
            jogo.get(
                "data",
                "9999-99-99"
            ),
            jogo.get(
                "nome",
                ""
            ).lower()
        )
    )


# =========================================================
# SALVAR JSON
# =========================================================

def salvar_json(jogos):

    dados = {

        "atualizado_em":
            date.today().isoformat(),

        "fonte":
            "RAWG Video Games Database",

        "creditos":
            "https://rawg.io/",

        "jogos":
            jogos
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        f"Arquivo criado: {OUTPUT_FILE}"
    )

    print(
        f"Jogos encontrados: {len(jogos)}"
    )


# =========================================================
# EXECUÇÃO
# =========================================================

def main():

    print(
        "=========================================="
    )

    print(
        " CavaloGameNews - Calendário de Lançamentos"
    )

    print(
        "=========================================="
    )

    jogos = buscar_lancamentos()

    jogos = remover_duplicados(
        jogos
    )

    jogos = ordenar_jogos(
        jogos
    )

    jogos = jogos[
        :LIMITE_JOGOS
    ]

    salvar_json(
        jogos
    )

    print()
    print(
        "Calendário atualizado com sucesso!"
    )


if __name__ == "__main__":

    main()
