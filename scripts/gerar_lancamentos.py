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

# Salva diretamente na raiz do repositório
PASTA_RAIZ = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

OUTPUT_FILE = os.path.join(
    PASTA_RAIZ,
    "lancamentos.json"
)

# Quantos dias para frente pesquisar
DIAS_FUTUROS = 120

# Quantos jogos guardar
LIMITE_JOGOS = 100


# =========================================================
# API KEY
# =========================================================

API_KEY = os.environ.get(
    "RAWG_API_KEY",
    ""
).strip()

if not API_KEY:

    print("ERRO: RAWG_API_KEY não encontrada.")
    print()
    print("Verifique o Secret RAWG_API_KEY no GitHub.")
    sys.exit(1)


# =========================================================
# CONSULTAR RAWG
# =========================================================

def consultar_rawg(params):

    parametros = dict(params)

    parametros["key"] = API_KEY

    url = (
        BASE_URL
        + "?"
        + urlencode(parametros)
    )

    print()
    print("Consultando RAWG...")
    print(
        url.replace(
            API_KEY,
            "***"
        )
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

    except HTTPError as erro:

        print()
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

        print()
        print(
            "ERRO DE CONEXÃO COM A RAWG:"
        )

        print(erro)

        sys.exit(1)

    except Exception as erro:

        print()
        print(
            "ERRO AO CONSULTAR A RAWG:"
        )

        print(erro)

        sys.exit(1)


# =========================================================
# IDENTIFICAR PLATAFORMAS
# =========================================================

def identificar_plataformas(game):

    resultado = []

    plataformas = game.get(
        "platforms",
        []
    )

    if not isinstance(
        plataformas,
        list
    ):
        return resultado

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

        # PC
        if (
            slug == "pc"
            or "windows" in slug
            or nome_lower == "pc"
        ):

            if "PC" not in resultado:

                resultado.append(
                    "PC"
                )

        # PlayStation
        if (
            "playstation" in slug
            or "playstation" in nome_lower
        ):

            if "PlayStation" not in resultado:

                resultado.append(
                    "PlayStation"
                )

        # Xbox
        if (
            "xbox" in slug
            or "xbox" in nome_lower
        ):

            if "Xbox" not in resultado:

                resultado.append(
                    "Xbox"
                )

        # Nintendo Switch
        if (
            "nintendo-switch" in slug
            or slug == "switch"
            or "switch" in nome_lower
        ):

            if "Switch" not in resultado:

                resultado.append(
                    "Switch"
                )

    return resultado


# =========================================================
# FORMATAR DATA
# =========================================================

def formatar_data(data):

    if not data:

        return ""

    try:

        partes = data.split("-")

        if len(partes) != 3:

            return data

        ano = partes[0]
        mes = partes[1]
        dia = partes[2]

        return f"{dia}/{mes}/{ano}"

    except Exception:

        return data


# =========================================================
# CRIAR ITEM
# =========================================================

def criar_item(game):

    nome = str(
        game.get(
            "name",
            ""
        )
    ).strip()

    data_lancamento = str(
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

        "data": data_lancamento,

        "data_formatada": formatar_data(
            data_lancamento
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

    fim = hoje + timedelta(
        days=DIAS_FUTUROS
    )

    data_inicio = hoje.isoformat()

    data_fim = fim.isoformat()

    print()
    print(
        "=========================================="
    )

    print(
        "PERÍODO DOS LANÇAMENTOS"
    )

    print(
        f"{data_inicio} até {data_fim}"
    )

    print(
        "=========================================="
    )


    # IDs de parent platforms:
    #
    # 1 = PC
    # 2 = PlayStation
    # 3 = Xbox
    # 7 = Nintendo
    #
    # A consulta já limita os resultados
    # às plataformas desejadas.

    params = {

        "dates":
            f"{data_inicio},{data_fim}",

        "ordering":
            "released",

        "parent_platforms":
            "1,2,3,7",

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


    print()
    print(
        f"Resultados recebidos da RAWG: {len(resultados)}"
    )


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


        # Sem nome
        if not item["nome"]:
            continue


        # Sem data
        if not item["data"]:
            continue


        # Sem imagem
        if not item["imagem"]:
            continue


        # Sem plataforma
        if not item["plataformas"]:
            continue


        jogos.append(
            item
        )


    print(
        f"Jogos válidos encontrados: {len(jogos)}"
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
        "ARQUIVO GERADO COM SUCESSO!"
    )

    print(
        "=========================================="
    )

    print(
        f"Arquivo: {OUTPUT_FILE}"
    )

    print(
        f"Jogos: {len(jogos)}"
    )

    print()


# =========================================================
# PRINCIPAL
# =========================================================

def main():

    print()
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


    # Confirmação extra
    # para o GitHub Actions.

    if not os.path.exists(
        OUTPUT_FILE
    ):

        print(
            "ERRO: o lancamentos.json não foi criado!"
        )

        sys.exit(1)


    tamanho = os.path.getsize(
        OUTPUT_FILE
    )


    print(
        f"OK: lancamentos.json existe."
    )

    print(
        f"Tamanho: {tamanho} bytes"
    )

    print()
    print(
        "Calendário atualizado com sucesso!"
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    main()
