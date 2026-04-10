import discord
from discord.ext import commands, tasks
import requests
import json
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1492203477689176144

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
# 🌐 API
# ========================

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://rubinot.com.br/worlds/Tenebrium"
}

def get_online_players():
    try:
        url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"

        res = session.get(url, headers=headers, timeout=10)

        print("Status:", res.status_code)

        if res.status_code != 200:
            return []

        data = res.json()
        return [p["name"] for p in data.get("players", [])]

    except Exception as e:
        print("Erro API:", e)
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
        value=f"<@{user_id}>"
    ).add_field(
        name="🎯 Player",
        value=player
    ).add_field(
        name="📌 Status",
        value="Adicionado" if action == "add" else "Removido"
    )

# ========================
# 🚀 READY
# ========================

@bot.event
async def on_ready():
    global last_online

    print(f"🔥 Bot online: {bot.user}")

    last_online = set(get_online_players())
    check_online.start()

# ========================
# 🔁 LOOP
# ========================

@tasks.loop(seconds=30)
async def check_online():
    global last_online

    current = set(get_online_players())
    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        print("Canal não encontrado")
        return

    for player in tracked_players:
        if player in current and player not in last_online:
            await channel.send(f"🟢 {player} LOGOU")

        if player not in current and player in last_online:
            await channel.send(f"🔴 {player} DESLOGOU")

    last_online = current

# ========================
# 📌 COMANDOS
# ========================

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)  # GARANTE STRING
    save_players()

    await ctx.send(embed=embed_hunted(name, "add", ctx.author.id))


@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    save_players()

    await ctx.send(embed=embed_hunted(name, "remove", ctx.author.id))


@bot.command()
async def list(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player.")
    else:
        await ctx.send("🎯 HUNTED:\n" + "\n".join(tracked_players))

# ========================
# ▶️ START
# ========================

bot.run(TOKEN)
