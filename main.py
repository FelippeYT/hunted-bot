import discord
from discord.ext import commands, tasks
import requests
import json
import os
from bs4 import BeautifulSoup

# ========================
# ⚙️ CONFIG
# ========================

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1492203477689176144  # coloca seu canal

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========================
# 📁 STORAGE
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
# 🌐 REQUEST
# ========================

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://rubinot.com.br/worlds/Tenebrium"
}

def get_online_players():
    try:
        url = "https://rubinot.com.br/worlds/Tenebrium"

        res = session.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            print("Erro status:", res.status_code)
            return []

        soup = BeautifulSoup(res.text, "html.parser")

        players = []

        for row in soup.select("table tbody tr"):
            cols = row.find_all("td")

            if len(cols) > 0:
                name = cols[0].text.strip()
                players.append(name)

        return players

    except Exception as e:
        print("Erro scraping:", e)
        return []

# ========================
# 🎨 EMBED
# ========================

def embed_hunted(player, action, user_id):
    return discord.Embed(
        title="🗡️ HUNTED SYSTEM",
        color=0x00ff00 if action == "add" else 0xff0000
    ).add_field(
        name="👤 Usuário",
        value=f"<@{user_id}>",
        inline=True
    ).add_field(
        name="🎯 Player",
        value=player,
        inline=True
    ).add_field(
        name="📌 Status",
        value="Adicionado à hunted" if action == "add" else "Removido da hunted",
        inline=False
    )

# ========================
# 🚀 READY
# ========================

@bot.event
async def on_ready():
    global last_online

    print(f"🔥 Bot online: {bot.user}")

    await bot.change_presence(activity=discord.Game(name="caçando players 👀"))

    # evita flood inicial
    last_online = set(get_online_players())

    check_online.start()

# ========================
# 🔁 LOOP
# ========================

@tasks.loop(seconds=60)
async def check_online():
    global last_online

    current = set(get_online_players())
    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        print("Canal não encontrado")
        return

    for player in tracked_players:

        if player in current and player not in last_online:
            await channel.send(f"🟢 **{player}** LOGOU")

        if player not in current and player in last_online:
            await channel.send(f"🔴 **{player}** DESLOGOU")

    last_online = current

# ========================
# 📌 COMANDOS
# ========================

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)
    save_players()

    embed = embed_hunted(name, "add", ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def untrack(ctx, *, name):
    tracked_players.discard(name)
    save_players()

    embed = embed_hunted(name, "remove", ctx.author.id)
    await ctx.send(embed=embed)

@bot.command()
async def list(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player na hunted.")
    else:
        await ctx.send("🎯 HUNTED:\n" + "\n".join(tracked_players))

# ========================
# ▶️ START
# ========================

bot.run(TOKEN)
