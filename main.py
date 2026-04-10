import discord
from discord.ext import commands, tasks
from discord import ui
import requests
import json
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1492203477689176144

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# STORAGE
# ========================

def load_players():
    try:
        with open("players.json", "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_players():
    with open("players.json", "w") as f:
        json.dump(list(tracked_players), f)

tracked_players = load_players()
last_online = set()

# ========================
# API (vai dar 403 às vezes)
# ========================

def get_online_players():
    try:
        url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://rubinot.com.br/worlds/Tenebrium"
        }

        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            print("Status:", res.status_code)
            return []

        data = res.json()
        return [p["name"] for p in data.get("players", [])]

    except:
        return []

# ========================
# MODAL
# ========================

class AddPlayerModal(ui.Modal, title="Adicionar Player"):
    name = ui.TextInput(label="Nome do player")

    async def on_submit(self, interaction: discord.Interaction):
        player = str(self.name)

        tracked_players.add(player)
        save_players()

        embed = discord.Embed(
            title="🟢 ADICIONADO",
            description=f"**{player}** foi adicionado",
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class RemovePlayerModal(ui.Modal, title="Remover Player"):
    name = ui.TextInput(label="Nome do player")

    async def on_submit(self, interaction: discord.Interaction):
        player = str(self.name)

        tracked_players.discard(player)
        save_players()

        embed = discord.Embed(
            title="🔴 REMOVIDO",
            description=f"**{player}** foi removido",
            color=0xff0000
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================
# VIEW (BOTÕES)
# ========================

class HuntedView(ui.View):

    @ui.button(label="➕ Adicionar", style=discord.ButtonStyle.success)
    async def add(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddPlayerModal())

    @ui.button(label="➖ Remover", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RemovePlayerModal())

    @ui.button(label="📜 Lista", style=discord.ButtonStyle.secondary)
    async def lista(self, interaction: discord.Interaction, button: ui.Button):
        if not tracked_players:
            msg = "📭 Nenhum player"
        else:
            msg = "\n".join(tracked_players)

        await interaction.response.send_message(msg, ephemeral=True)

# ========================
# COMANDO PAINEL
# ========================

@bot.command()
async def painel(ctx):
    embed = discord.Embed(
        title="🗡️ HUNTED SYSTEM",
        description="Gerencie sua lista de hunted",
        color=0x2f3136
    )

    await ctx.send(embed=embed, view=HuntedView())

# ========================
# LOOP
# ========================

@tasks.loop(seconds=30)
async def check_online():
    global last_online

    current = set(get_online_players())
    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        return

    for player in tracked_players:
        if player in current and player not in last_online:
            await channel.send(f"🟢 {player} LOGOU")

        if player not in current and player in last_online:
            await channel.send(f"🔴 {player} DESLOGOU")

    last_online = current

# ========================
# READY
# ========================

@bot.event
async def on_ready():
    print(f"🔥 {bot.user} online")

    global last_online
    last_online = set(get_online_players())

    check_online.start()

# ========================
# START
# ========================

bot.run(TOKEN)
