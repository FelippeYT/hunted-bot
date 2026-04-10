import discord
from discord.ext import commands, tasks
import requests
import json
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FILE = "players.json"

tracked_players = set()
online_players = set()

# ------------------ LOAD / SAVE ------------------

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
    try:
        url = f"https://rubinot.com.br/characters?name={name.replace(' ', '%20')}"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/x-component",
            "Referer": "https://rubinot.com.br/"
        }

        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return None

        text = res.text.lower()

        if "online" in text:
            return True
        if "offline" in text:
            return False

        return None

    except:
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
    name = str(name).strip()
    tracked_players.add(name)
    save_players()
    await ctx.send(f"✅ {name} adicionado ao tracking")

@bot.command()
async def untrack(ctx, *, name):
    name = str(name).strip()
    tracked_players.discard(name)
    save_players()
    await ctx.send(f"❌ {name} removido")

@bot.command(name="list")
async def list_cmd(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player sendo trackado")
    else:
        await ctx.send("📜 Players:\n" + "\n".join(tracked_players))

# ------------------ LOOP ------------------

@tasks.loop(seconds=60)
async def check_players():
    for player in list(tracked_players):
        status = get_player_status(player)

        if status is None:
            continue

        if status and player not in online_players:
            online_players.add(player)
            await notify(f"🟢 {player} entrou no jogo!")

        elif not status and player in online_players:
            online_players.remove(player)
            await notify(f"🔴 {player} saiu do jogo!")

# ------------------ NOTIFY ------------------

async def notify(msg):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(msg)
                    return
                except:
                    continue

# ------------------ RUN ------------------

bot.run(TOKEN)
