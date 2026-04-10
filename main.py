import discord
from discord.ext import commands, tasks
import requests
import json
import os

# ========================
# ⚙️ CONFIG
# ========================

TOKEN = os.getenv("TOKEN")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")  # 👈 COOKIE AQUI
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
# 🌐 SESSION
# ========================

session = requests.Session()

# ========================
# 🌐 API RUBINOT (COM COOKIE)
# ========================

def get_online_players():
    try:
        url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Referer": "https://rubinot.com.br/worlds/Tenebrium",
        }

        cookies = {
            "cf_clearance": CF_CLEARANCE
        }

        res = session.get(url, headers=headers, cookies=cookies, timeout=10)

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
