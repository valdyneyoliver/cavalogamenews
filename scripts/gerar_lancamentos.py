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

# Quantos dias no futuro serão pesquisados
DIAS_FUTUROS = 120

# Quantos jogos serão salvos
LIMITE_JOGOS = 100

# Quantas páginas da RAWG serão consultadas
MAX_PAGINAS = 5

# Jogos por página
JOGOS_POR_PAGINA = 40


# =========================================================
# API KEY
# =========================================================

API_KEY = os.environ.get("RAWG_API_KEY", "").strip()

if not API_KEY:
    print("ERRO: RAWG_API_KEY não foi encontrada.")
    print()
    print("Configure o Secret no GitHub com o nome:")
    print()
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

            return json.loads(conteudo)

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
        print("ERRO DE CONEXÃO COM A RAWG:")
        print(erro)

        sys.exit(1)

    except Exception as erro:

        print()
        print("ERRO AO CONSULTAR A RAWG:")
        print(erro)

        sys.exit(1)


# =========================================================
# IDENTIFICAR PLATAFORMAS
# =========================================================

def identificar_plataformas(game):

    encontradas = []

    plataformas = game.get(
        "platforms",
        []
    )

    if not isinstance(
        plataformas,
        list
    ):
        return encontradas

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

        # =================================================
        # PC
        # =================================================

        if (
            slug == "pc"
            or "windows" in slug
            or nome_lower == "pc"
            or "windows" in nome_lower
        ):

            if "PC" not in encontradas:

                encontradas.append(
                    "PC"
                )


        # =================================================
        # PLAYSTATION
        # =================================================

        if (
            "playstation" in slug
            or "playstation" in nome_lower
            or slug in [
                "ps5",
                "ps4"
            ]
        ):

            if "PlayStation" not in encontradas:

                encontradas.append(
                    "PlayStation"
                )


        # =================================================
        # XBOX
        # =================================================

        if (
            "xbox" in slug
            or "xbox" in nome_lower
        ):

            if "Xbox" not in encontradas:

                encontradas.append(
                    "Xbox"
                )


        # =================================================
        # NINTENDO SWITCH
        # =================================================

        if (
            "nintendo-switch" in slug
            or slug == "switch"
            or "switch" in slug
            or "switch" in nome_lower
        ):

            if "Switch" not in encontradas:

                encontradas.append(
                    "Switch"
                )

    return encontradas


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
# LIMPAR TEXTO
# =========================================================

def limpar_texto(valor):

    if valor is None:
        return ""

    return (
        str(valor)
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


# =========================================================
# CRIAR ITEM
# =========================================================

def criar_item(game):

    nome = limpar_texto(
        game.get(
            "name",
            ""
        )
    )

    slug = limpar_texto(
        game.get(
            "slug",
            ""
        )
    )

    data_lancamento = limpar_texto(
        game.get(
            "released",
            ""
        )
    )

    imagem = limpar_texto(
        game.get(
            "background_image",
            ""
        )
    )

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

        "data_formatada":
            formatar_data(
                data_lancamento
            ),

        "imagem": imagem,

        "plataformas": plataformas,

        "link_rawg":
            (
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
    print("==========================================")
    print("PERÍODO DOS LANÇAMENTOS")
    print("==========================================")
    print(
        f"{data_inicio} até {data_fim}"
    )

    jogos = []

    # =====================================================
    # PAGINAÇÃO
    # =====================================================

    for pagina in range(
        1,
        MAX_PAGINAS + 1
    ):

        print()
        print(
            f"Buscando página {pagina}/{MAX_PAGINAS}..."
        )

        params = {

            "dates":
                f"{data_inicio},{data_fim}",

            "ordering":
                "released",

            "page":
                pagina,

            "page_size":
                JOGOS_POR_PAGINA

        }

        dados = consultar_rawg(
            params
        )

        resultados = dados.get(
            "results",
            []
        )

        if not isinstance(
            resultados,
            list
        ):
            resultados = []

        print(
            f"Jogos recebidos: {len(resultados)}"
        )

        if not resultados:
            break

        for game in resultados:

            if not isinstance(
                game,
                dict
            ):
                continue

            item = criar_item(
                game
            )

            # =================================================
            # VALIDAÇÕES
            # =================================================

            if not item["id"]:
                continue

            if not item["nome"]:
                continue

            if not item["data"]:
                continue

            if not item["imagem"]:
                continue

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
# ORDENAR POR DATA
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
# REMOVER JOGOS COM DATA INVÁLIDA
# =========================================================

def validar_datas(jogos):

    resultado = []

    hoje = date.today()

    limite = (
        hoje
        + timedelta(
            days=DIAS_FUTUROS
        )
    )

    for jogo in jogos:

        data_string = jogo.get(
            "data",
            ""
        )

        try:

            ano, mes, dia = map(
                int,
                data_string.split("-")
            )

            data_jogo = date(
                ano,
                mes,
                dia
            )

        except Exception:

            continue

        if (
            data_jogo >= hoje
            and data_jogo <= limite
        ):

            resultado.append(
                jogo
            )

    return resultado


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
    print("==========================================")
    print("JSON GERADO COM SUCESSO")
    print("==========================================")

    print(
        f"Arquivo: {OUTPUT_FILE}"
    )

    print(
        f"Total de jogos: {len(jogos)}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("==========================================")
    print(" CAVALOGAMENEWS")
    print(" CALENDÁRIO DE LANÇAMENTOS")
    print("==========================================")

    print()
    print(
        "Iniciando busca na RAWG..."
    )

    # Buscar
    jogos = buscar_lancamentos()

    print()
    print(
        f"Total encontrado inicialmente: {len(jogos)}"
    )

    # Remover duplicados
    jogos = remover_duplicados(
        jogos
    )

    print(
        f"Após remover duplicados: {len(jogos)}"
    )

    # Validar datas
    jogos = validar_datas(
        jogos
    )

    print(
        f"Após validar datas: {len(jogos)}"
    )

    # Ordenar
    jogos = ordenar_jogos(
        jogos
    )

    # Limitar
    jogos = jogos[
        :LIMITE_JOGOS
    ]

    # Salvar
    salvar_json(
        jogos
    )

    print()
    print("==========================================")
    print(" CALENDÁRIO ATUALIZADO!")
    print("==========================================")


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    main()
