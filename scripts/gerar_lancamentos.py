import json
import os
import time
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ==========================================
# CONFIGURAÇÕES
# ==========================================

API_URL = "https://api.rawg.io/api/games"
ARQUIVO_SAIDA = "lancamentos.json"

DIAS_FUTUROS = 120
LIMITE = 100

# Limites para evitar que o GitHub Actions fique preso por muitos minutos.
TENTATIVAS = 5
TEMPO_ESPERA = 5
TIMEOUT = 20
ESPERA_MAXIMA = 30


# ==========================================
# CHAVE DA RAWG
# ==========================================

API_KEY = os.environ.get("RAWG_API_KEY")

if not API_KEY:
    print("ERRO: RAWG_API_KEY não encontrada.", flush=True)
    raise SystemExit(1)


# ==========================================
# DATAS
# ==========================================

hoje = date.today()
fim = hoje + timedelta(days=DIAS_FUTUROS)

data_inicio = hoje.strftime("%Y-%m-%d")
data_fim = fim.strftime("%Y-%m-%d")

print("===================================", flush=True)
print("CavaloGameNews", flush=True)
print("Gerador de Lançamentos", flush=True)
print("===================================", flush=True)
print("Período:", data_inicio, "até", data_fim, flush=True)


# ==========================================
# CONSULTAR RAWG COM NOVAS TENTATIVAS
# ==========================================

parametros = {
    "key": API_KEY,
    "dates": f"{data_inicio},{data_fim}",
    "ordering": "released",
    "parent_platforms": "1,2,3,7",
    "page_size": 100
}

url = API_URL + "?" + urlencode(parametros)


def consultar_rawg():
    erros_temporarios = {429, 500, 502, 503, 504, 522}

    for tentativa in range(1, TENTATIVAS + 1):
        print(
            f"Consultando RAWG... tentativa {tentativa}/{TENTATIVAS}",
            flush=True
        )

        request = Request(
            url,
            headers={
                "User-Agent": "CavaloGameNews/1.0",
                "Accept": "application/json"
            }
        )

        try:
            with urlopen(request, timeout=TIMEOUT) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))

            print("Resposta da RAWG recebida.", flush=True)
            return dados

        except HTTPError as erro:
            print(f"Erro HTTP {erro.code}: {erro.reason}", flush=True)

            if erro.code not in erros_temporarios:
                raise

            if tentativa == TENTATIVAS:
                raise

            retry_after = erro.headers.get("Retry-After")
            try:
                espera = int(retry_after) if retry_after else TEMPO_ESPERA * tentativa
            except (TypeError, ValueError):
                espera = TEMPO_ESPERA * tentativa

            espera = max(1, min(espera, ESPERA_MAXIMA))

        except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as erro:
            print(f"Falha temporária de conexão/resposta: {erro}", flush=True)

            if tentativa == TENTATIVAS:
                raise

            espera = min(TEMPO_ESPERA * tentativa, ESPERA_MAXIMA)

        print(f"Nova tentativa em {espera} segundos...", flush=True)
        time.sleep(espera)

    raise RuntimeError("Não foi possível consultar a RAWG após várias tentativas.")


try:
    dados = consultar_rawg()
except Exception as erro:
    print(
        "ERRO: não foi possível consultar a RAWG após várias tentativas.",
        flush=True
    )
    print(erro, flush=True)
    raise SystemExit(1)


# ==========================================
# PEGAR RESULTADOS
# ==========================================

resultados = dados.get("results", [])
print("Jogos recebidos:", len(resultados), flush=True)

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

    for item in jogo.get("platforms", []) or []:
        plataforma = item.get("platform", {})
        nome_plataforma = plataforma.get("name", "")
        nome_lower = nome_plataforma.lower()

        if nome_lower == "pc":
            if "PC" not in plataformas:
                plataformas.append("PC")

        elif "playstation" in nome_lower:
            if "PlayStation" not in plataformas:
                plataformas.append("PlayStation")

        elif "xbox" in nome_lower:
            if "Xbox" not in plataformas:
                plataformas.append("Xbox")

        elif "switch" in nome_lower:
            if "Switch" not in plataformas:
                plataformas.append("Switch")

    # Ignorar jogos com informações incompletas.
    if not nome or not data_lancamento or not imagem or not plataformas:
        continue

    partes = data_lancamento.split("-")
    data_formatada = (
        f"{partes[2]}/{partes[1]}/{partes[0]}"
        if len(partes) == 3
        else data_lancamento
    )

    jogos.append({
        "id": jogo.get("id"),
        "nome": nome,
        "slug": slug,
        "data": data_lancamento,
        "data_formatada": data_formatada,
        "imagem": imagem,
        "plataformas": plataformas,
        "link_rawg": f"https://rawg.io/games/{slug}" if slug else ""
    })


# ==========================================
# REMOVER DUPLICADOS
# ==========================================

unicos = {}

for jogo in jogos:
    unicos[jogo["id"]] = jogo

jogos = list(unicos.values())


# ==========================================
# ORDENAR E LIMITAR
# ==========================================

jogos.sort(
    key=lambda jogo: (
        jogo["data"],
        jogo["nome"].lower()
    )
)

jogos = jogos[:LIMITE]

print("Jogos válidos:", len(jogos), flush=True)


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

with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as arquivo:
    json.dump(
        dados_saida,
        arquivo,
        ensure_ascii=False,
        indent=2
    )

print("===================================", flush=True)
print("lancamentos.json criado!", flush=True)
print("Jogos:", len(jogos), flush=True)
print("===================================", flush=True)
