#!/usr/bin/env python3

import os
import json
import asyncio
from pathlib import Path

import discord
from discord.ext import commands

ARQUIVO_NOTICIAS = Path("noticias_pendentes.json")
ARQUIVO_ENVIADAS = Path("noticias_enviadas_discord.json")

CANAL_ID = 1565843110431555694
TOKEN = os.getenv("DISCORD_BOT_TOKEN")


def carregar_json(arquivo, padrao):
    if not arquivo.exists():
        return padrao

    with arquivo.open("r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(arquivo, dados):
    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )


class AprovacaoView(discord.ui.View):
    def __init__(self, noticia):
        super().__init__(timeout=None)
        self.noticia = noticia

    async def finalizar(self, interaction, status):
        noticias = carregar_json(ARQUIVO_NOTICIAS, [])

        encontrada = False

        for noticia in noticias:
            if str(noticia.get("id")) == str(self.noticia["id"]):
                if noticia.get("status") != "pendente":
                    await interaction.response.send_message(
                        "Esta notícia já foi analisada.",
                        ephemeral=True
                    )
                    return

                noticia["status"] = status
                encontrada = True
                break

        if not encontrada:
            await interaction.response.send_message(
                "Notícia não encontrada.",
                ephemeral=True
            )
            return

        salvar_json(ARQUIVO_NOTICIAS, noticias)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"**{self.noticia['titulo']}**\n"
                    f"Decisão: {'🟢 Aprovada' if status == 'aprovada' else '🔴 Rejeitada'}",
            view=self
        )

    @discord.ui.button(
        label="Aprovar",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="noticia_aprovar"
    )
    async def aprovar(self, interaction, button):
        await self.finalizar(interaction, "aprovada")

    @discord.ui.button(
        label="Rejeitar",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="noticia_rejeitar"
    )
    async def rejeitar(self, interaction, button):
        await self.finalizar(interaction, "rejeitada")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Bot conectado: {bot.user}")

    canal = bot.get_channel(CANAL_ID)

    if canal is None:
        try:
            canal = await bot.fetch_channel(CANAL_ID)
        except discord.HTTPException as erro:
            print(f"Erro ao acessar canal: {erro}")
            await bot.close()
            return

    noticias = carregar_json(ARQUIVO_NOTICIAS, [])
    enviadas = carregar_json(ARQUIVO_ENVIADAS, [])

    ids_enviados = set(enviadas)

    for noticia in noticias:
        if noticia.get("status") != "pendente":
            continue

        noticia_id = str(noticia.get("id", ""))

        if not noticia_id or noticia_id in ids_enviados:
            continue

        embed = discord.Embed(
            title=noticia.get("titulo", "Nova notícia")[:256],
            description=noticia.get("resumo", "Sem resumo disponível.")[:4096],
            color=discord.Color.green()
        )

        embed.add_field(
            name="Categoria",
            value=noticia.get("categoria", "Notícia"),
            inline=True
        )

        embed.add_field(
            name="Fonte",
            value=noticia.get("fonte", "Não informada"),
            inline=True
        )

        link = noticia.get("link_original", "")

        if link.startswith("https://"):
            embed.add_field(
                name="Link da notícia",
                value=f"[Abrir notícia]({link})",
                inline=False
            )

        embed.set_footer(text="CavaloGameNews • Central de aprovação")

        view = AprovacaoView(noticia)

        try:
            await canal.send(embed=embed, view=view)
            ids_enviados.add(noticia_id)
            salvar_json(ARQUIVO_ENVIADAS, sorted(ids_enviados))
            print(f"[OK] Enviada: {noticia.get('titulo')}")

        except discord.HTTPException as erro:
            print(f"[ERRO] Não foi possível enviar: {erro}")

    await bot.close()


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN não configurado.")

    bot.run(TOKEN)
