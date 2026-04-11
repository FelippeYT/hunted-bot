import os
import time
import asyncio
import requests
import discord
from discord.ext import commands, tasks

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN")

WORLD_API = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players = set()

session = requests.Session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://rubinot.com.br/worlds/Tenebrium",
    "Origin": "https://rubinot.com.br",
    "Connection": "keep-alive"
}

# =========================
# CLOUDFARE SESSION INIT
# =========================

def init_session():
    try:
        session.get("https://rubinot.com.br/worlds/Tenebrium", headers=HEADERS, timeout=10)
        print("🟢 Session inicializada")
    except Exception as e:
        print("Erro init session:", e)

# =========================
# API FETCH
# =========================

def get_world_data():
    try:
        res = session.get(WORLD_API, headers=HEADERS, timeout=10)

        if res.status_code != 200:
            print("Bloqueado API:", res.status_code)
            return None

        return res.json()

    except Exception as e:
        print("Erro API:", e)
        return None

# =========================
# PLAYER STATUS
# =========================

def get_player_status(name: str):
    data = get_world_data()
    if not data:
        return None

    # estrutura comum: data["characters"]
    characters = data.get("characters", [])

    for char in characters:
        char_name = char.get("name", "").lower()
        if char_name == name.lower():
            return char.get("online", False)

    return None

# =========================
# DISCORD EVENTS
# =========================

@bot.event
async def on_ready():
    print(f"🔥 Bot online: {bot.user}")

    init_session()
    check_players.start()

# =========================
# COMMANDS
# =========================

@bot.command()
async def track(ctx, *, name):
    name = name.strip()
    tracked_players.add(name)
    await ctx.send(f"✅ {name} adicionado ao tracking")

@bot.command()
async def untrack(ctx, *, name):
    name = name.strip()
    tracked_players.discard(name)
    await ctx.send(f"❌ {name} removido do tracking")

@bot.command(name="list")
async def list_cmd(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player sendo trackado")
        return

    await ctx.send("📜 Players:\n" + "\n".join(tracked_players))

@bot.command()
async def online(ctx):
    if not online_players:
        await ctx.send("🔴 Ninguém online agora")
        return

    await ctx.send("🟢 Online:\n" + "\n".join(online_players))

# =========================
# LOOP CHECK
# =========================

@tasks.loop(seconds=60)
async def check_players():
    for player in list(tracked_players):

        status = get_player_status(player)

        if status is None:
            continue

        # entrou
        if status and player not in online_players:
            online_players.add(player)
            await notify(f"🟢 {player} entrou no jogo!")

        # saiu
        elif not status and player in online_players:
            online_players.remove(player)
            await notify(f"🔴 {player} saiu do jogo!")

# =========================
# NOTIFY
# =========================

async def notify(message):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(message)
                    return
                except:
                    continue

# =========================
# RUN BOT
# =========================

bot.run(TOKEN)
