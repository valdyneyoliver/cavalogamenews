import json
import os
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ==========================================
# CONFIGURAÇÕES
# ==========================================

API_URL = "https://api.rawg.io/api/games"

ARQUIVO_SAIDA = "lancamentos.json"

DIAS_FUTUROS = 120

LIMITE = 100


# ==========================================
# CHAVE DA RAWG
# ==========================================

API_KEY = os.environ.get("RAWG_API_KEY")

if not API_KEY:
    print("ERRO: RAWG_API_KEY não encontrada.")
    exit(1)


# ==========================================
# DATAS
# ==========================================

hoje = date.today()

fim = hoje + timedelta(days=DIAS_FUTUROS)

data_inicio = hoje.strftime("%Y-%m-%d")

data_fim = fim.strftime("%Y-%m-%d")


print("===================================")
print("CavaloGameNews")
print("Gerador de Lançamentos")
print("===================================")

print("Período:")
print(data_inicio, "até", data_fim)


# ==========================================
# CONSULTAR RAWG
# ==========================================

parametros = {
    "key": API_KEY,
    "dates": f"{data_inicio},{data_fim}",
    "ordering": "released",
    "parent_platforms": "1,2,3,7",
    "page_size": 100
}

url = API_URL + "?" + urlencode(parametros)

print("Consultando RAWG...")

request = Request(
    url,
    headers={
        "User-Agent": "CavaloGameNews"
    }
)

try:

    with urlopen(request, timeout=30) as resposta:

        dados = json.loads(
            resposta.read().decode("utf-8")
        )

except Exception as erro:

    print("ERRO ao consultar RAWG:")
    print(erro)
    exit(1)


# ==========================================
# PEGAR RESULTADOS
# ==========================================

resultados = dados.get("results", [])

print("Jogos recebidos:", len(resultados))


jogos = []


# ==========================================
# PROCESSAR JOGOS
# ==========================================

for jogo in resultados:

    nome = jogo.get("name")

    data_lancamento = jogo.get("released")

    imagem = jogo.get("background_image")

    slug = jogo.get("slug")

    plataformas = []


    # --------------------------------------
    # PLATAFORMAS
    # --------------------------------------

    for item in jogo.get("platforms", []):

        plataforma = item.get("platform", {})

        nome_plataforma = plataforma.get(
            "name",
            ""
        )

        nome_lower = nome_plataforma.lower()


        if nome_lower == "pc":

            if "PC" not in plataformas:
                plataformas.append("PC")


        elif "playstation" in nome_lower:

            if "PlayStation" not in plataformas:
                plataformas.append(
                    "PlayStation"
                )


        elif "xbox" in nome_lower:

            if "Xbox" not in plataformas:
                plataformas.append("Xbox")


        elif "switch" in nome_lower:

            if "Switch" not in plataformas:
                plataformas.append("Switch")


    # --------------------------------------
    # IGNORAR JOGO INCOMPLETO
    # --------------------------------------

    if not nome:
        continue

    if not data_lancamento:
        continue

    if not imagem:
        continue

    if not plataformas:
        continue


    # --------------------------------------
    # DATA FORMATADA
    # --------------------------------------

    partes = data_lancamento.split("-")

    data_formatada = (
        f"{partes[2]}/{partes[1]}/{partes[0]}"
        if len(partes) == 3
        else data_lancamento
    )


    # --------------------------------------
    # ADICIONAR JOGO
    # --------------------------------------

    jogos.append({

        "id": jogo.get("id"),

        "nome": nome,

        "slug": slug,

        "data": data_lancamento,

        "data_formatada": data_formatada,

        "imagem": imagem,

        "plataformas": plataformas,

        "link_rawg": (
            f"https://rawg.io/games/{slug}"
            if slug
            else ""
        )

    })


# ==========================================
# REMOVER DUPLICADOS
# ==========================================

unicos = {}

for jogo in jogos:

    unicos[jogo["id"]] = jogo


jogos = list(unicos.values())


# ==========================================
# ORDENAR
# ==========================================

jogos.sort(
    key=lambda jogo: (
        jogo["data"],
        jogo["nome"].lower()
    )
)


# ==========================================
# LIMITE
# ==========================================

jogos = jogos[:LIMITE]


print("Jogos válidos:", len(jogos))


# ==========================================
# CRIAR JSON
# ==========================================

dados_saida = {

    "atualizado_em": date.today().isoformat(),

    "fonte": "RAWG",

    "jogos": jogos

}


# ==========================================
# SALVAR
# ==========================================

with open(
    ARQUIVO_SAIDA,
    "w",
    encoding="utf-8"
) as arquivo:

    json.dump(
        dados_saida,
        arquivo,
        ensure_ascii=False,
        indent=2
    )


print("===================================")
print("lancamentos.json criado!")
print("Jogos:", len(jogos))
print("===================================")
