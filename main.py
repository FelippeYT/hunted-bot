import discord
from discord.ext import commands, tasks
import requests
import json
import asyncio
import re
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)

FILE = "players.json"
tracked_players = set()
online_players = set()

# ------------------ LOAD/SAVE ------------------

def load_players():
    global tracked_players
    try:
        with open(FILE, "r") as f:
            tracked_players = set(json.load(f))
    except:
        tracked_players = set()

def save_players():
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)

# ------------------ SCRAPER ------------------

def get_player_status(name):
    url = f"https://rubinot.com.br/characters?name={name.replace(' ', '%20')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/x-component",
        "Referer": "https://rubinot.com.br/"
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return None

        text = res.text.lower()

        # 💡 DETECÇÃO SIMPLES (ajustável)
        if "online" in text:
            return True
        elif "offline" in text:
            return False

        return None

    except Exception as e:
        print("Erro scraping:", e)
        return None

# ------------------ EVENTS ------------------

@bot.event
async def on_ready():
    print(f"🔥 Bot online: {bot.user}")
    load_players()
    check_players.start()

# ------------------ COMMANDS ------------------

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)
    save_players()
    await ctx.send(f"✅ {name} foi adicionado ao tracking")

@bot.command()
async def untrack(ctx, *, name):
    tracked_players.discard(name)
    save_players()
    await ctx.send(f"❌ {name} removido")

@bot.command()
async def list(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player sendo trackado")
    else:
        msg = "\n".join(tracked_players)
        await ctx.send(f"📜 Players:\n{msg}")

# ------------------ LOOP ------------------

@tasks.loop(seconds=60)  # pode mudar pra 30 ou 120
async def check_players():
    global online_players

    for player in tracked_players:
        status = get_player_status(player)

        if status is None:
            continue

        # ficou online
        if status and player not in online_players:
            online_players.add(player)
            await notify(f"🟢 {player} entrou no jogo!")

        # ficou offline
        elif not status and player in online_players:
            online_players.remove(player)
            await notify(f"🔴 {player} saiu do jogo!")

# ------------------ NOTIFY ------------------

async def notify(message):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(message)
                    return
                except:
                    continue

# ------------------ RUN ------------------

bot.run(TOKEN)
