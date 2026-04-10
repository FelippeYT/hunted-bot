import discord
from discord.ext import commands, tasks
import requests
import json
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 123456789123456789  # coloca o ID do canal aqui

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

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

def get_online_players():
    try:
        url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
        data = requests.get(url).json()
        return [p["name"] for p in data["players"]]
    except Exception as e:
        print("Erro API:", e)
        return []

# ========================
# 🎨 EMBED
# ========================

def embed_hunted(player, action, user_id):
    return discord.Embed(
        title="🗡️ SISTEMA DE HUNTED",
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
# 🚀 EVENTO READY
# ========================

@bot.event
async def on_ready():
    print(f"🔥 Bot online: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="caçando players 👀"))
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
        return

    for player in tracked_players:

        # LOGOU
        if player in current and player not in last_online:
            await channel.send(f"🟢 {player} LOGOU")

        # DESLOGOU
        if player not in current and player in last_online:
            await channel.send(f"🔴 {player} DESLOGOU")

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

bot.run("MTQ5MjAzMzMxODY1OTgyMTYxOQ.GCWike.9D6O8qGlZ5l86NBVdFS3O0Fko5JmCkBTTDF254")