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

DIAS_FUTUROS = 120

LIMITE_JOGOS = 100


# =========================================================
# API KEY
# =========================================================

API_KEY = os.environ.get("RAWG_API_KEY", "").strip()

if not API_KEY:
    print("ERRO: a variável RAWG_API_KEY não foi encontrada.")
    print()
    print("Verifique no GitHub:")
    print("Settings > Secrets and variables > Actions")
    print()
    print("O nome do Secret deve ser exatamente:")
    print("RAWG_API_KEY")
    print()

    sys.exit(1)


# =========================================================
# CONSULTAR RAWG
# =========================================================

def consultar_rawg(params):

    params = dict(params)

    params["key"] = API_KEY

    url = BASE_URL + "?" + urlencode(params)

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

            conteudo = response.read().decode(
                "utf-8"
            )

            return json.loads(
                conteudo
            )

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
            "ERRO DE CONEXÃO COM A RAWG:"
        )

        print(erro)

        sys.exit(1)

    except Exception as erro:

        print(
            "ERRO AO CONSULTAR A RAWG:"
        )

        print(erro)

        sys.exit(1)


# =========================================================
# CONSULTAR DETALHES DO JOGO
#
# A busca inicial da RAWG pode trazer somente
# background_image.
#
# Aqui fazemos uma segunda consulta para tentar
# encontrar a imagem vertical/original da capa.
# =========================================================

def consultar_detalhes_jogo(game_id):

    if not game_id:
        return {}

    url = (
        f"{BASE_URL}/{game_id}"
        f"?key={API_KEY}"
    )

    print(
        f"  Buscando capa original do jogo ID {game_id}..."
    )

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

            conteudo = response.read().decode(
                "utf-8"
            )

            return json.loads(
                conteudo
            )

    except Exception as erro:

        print(
            f"  Não foi possível buscar detalhes: {erro}"
        )

        return {}


# =========================================================
# ESCOLHER IMAGEM
#
# PRIORIDADE:
#
# 1. imagem vertical/original encontrada
# 2. background_image da RAWG
#
# A RAWG nem sempre fornece uma capa vertical
# para todos os jogos.
# =========================================================

def escolher_imagem(game, detalhes):

    # -----------------------------------------------------
    # 1. Tentar imagem principal dos detalhes
    # -----------------------------------------------------

    imagem = str(
        detalhes.get(
            "background_image",
            ""
        )
    ).strip()

    if imagem:
        return imagem


    # -----------------------------------------------------
    # 2. Tentar imagem recebida na busca inicial
    # -----------------------------------------------------

    imagem = str(
        game.get(
            "background_image",
            ""
        )
    ).strip()

    if imagem:
        return imagem


    # -----------------------------------------------------
    # 3. Nenhuma imagem
    # -----------------------------------------------------

    return ""


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

        nome_lower = nome.lower()


        # -------------------------------------------------
        # PC
        # -------------------------------------------------

        if (
            slug == "pc"
            or "windows" in slug
            or nome_lower == "pc"
        ):

            if "PC" not in plataformas_encontradas:

                plataformas_encontradas.append(
                    "PC"
                )


        # -------------------------------------------------
        # PlayStation
        # -------------------------------------------------

        if (
            "playstation" in slug
            or "playstation" in nome_lower
        ):

            if "PlayStation" not in plataformas_encontradas:

                plataformas_encontradas.append(
                    "PlayStation"
                )


        # -------------------------------------------------
        # Xbox
        # -------------------------------------------------

        if (
            "xbox" in slug
            or "xbox" in nome_lower
        ):

            if "Xbox" not in plataformas_encontradas:

                plataformas_encontradas.append(
                    "Xbox"
                )


        # -------------------------------------------------
        # Nintendo Switch
        # -------------------------------------------------

        if (
            "nintendo-switch" in slug
            or slug == "switch"
            or "switch" in nome_lower
        ):

            if "Switch" not in plataformas_encontradas:

                plataformas_encontradas.append(
                    "Switch"
                )


    return plataformas_encontradas


# =========================================================
# FORMATAR DATA
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
# LIMPAR NOME
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
# CRIAR ITEM
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


    # -----------------------------------------------------
    # Buscar detalhes para tentar conseguir
    # a imagem original/capa
    # -----------------------------------------------------

    detalhes = consultar_detalhes_jogo(
        game_id
    )


    imagem = escolher_imagem(
        game,
        detalhes
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
        "=========================================="
    )

    print(
        "Período pesquisado:"
    )

    print(
        f"{data_inicio} até {data_fim}"
    )

    print(
        "=========================================="
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


    for numero, game in enumerate(
        resultados,
        start=1
    ):

        if not isinstance(
            game,
            dict
        ):
            continue


        print()
        print(
            f"[{numero}/{len(resultados)}] "
            f"{game.get('name', 'Sem nome')}"
        )


        item = criar_item(
            game
        )


        # -------------------------------------------------
        # Ignorar jogo sem nome
        # -------------------------------------------------

        if not item["nome"]:

            print(
                "  Ignorado: sem nome."
            )

            continue


        # -------------------------------------------------
        # Ignorar jogo sem data
        # -------------------------------------------------

        if not item["data"]:

            print(
                "  Ignorado: sem data."
            )

            continue


        # -------------------------------------------------
        # Ignorar jogo sem imagem
        # -------------------------------------------------

        if not item["imagem"]:

            print(
                "  Ignorado: sem imagem."
            )

            continue


        # -------------------------------------------------
        # Ignorar jogo sem plataforma compatível
        # -------------------------------------------------

        if not item["plataformas"]:

            print(
                "  Ignorado: sem plataforma compatível."
            )

            continue


        print(
            "  ✓ Adicionado"
        )

        print(
            f"  Data: {item['data_formatada']}"
        )

        print(
            f"  Plataformas: "
            f"{', '.join(item['plataformas'])}"
        )

        print(
            f"  Imagem: encontrada"
        )


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
        "=========================================="
    )

    print(
        f"Arquivo criado: {OUTPUT_FILE}"
    )

    print(
        f"Jogos encontrados: {len(jogos)}"
    )

    print(
        "=========================================="
    )


# =========================================================
# EXECUÇÃO
# =========================================================

def main():

    print(
        "=========================================="
    )

    print(
        " CavaloGameNews"
    )

    print(
        " Calendário de Lançamentos"
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


# =========================================================
# INICIAR
# =========================================================

if __name__ == "__main__":

    main()
