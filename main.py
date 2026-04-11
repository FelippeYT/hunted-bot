import discord
from discord.ext import commands, tasks
import requests
import json
import os
import threading
from flask import Flask

TOKEN = os.getenv("TOKEN")

# ---------------- DISCORD BOT ----------------

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players = set()
FILE = "players.json"

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

def get_player_status(name):
    try:
        url = f"https://rubinot.com.br/characters?name={name.replace(' ', '%20')}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        }

        res = requests.get(url, headers=headers, timeout=10)
        text = res.text.lower()

        if "online" in text:
            return True
        if "offline" in text:
            return False

        return None
    except:
        return None

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

async def notify(msg):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(msg)
                    return
                except:
                    pass

@bot.event
async def on_ready():
    print(f"🔥 Bot online: {bot.user}")
    load_players()
    check_players.start()

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)
    save_players()
    await ctx.send(f"✅ {name} adicionado")

@bot.command(name="list")
async def list_cmd(ctx):
    await ctx.send("\n".join(tracked_players) if tracked_players else "vazio")


def run_bot():
    bot.run(TOKEN)


# ---------------- FLASK DASHBOARD ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot online OK"

def run_flask():
    app.run(host="0.0.0.0", port=5000)


# ---------------- START BOTH ----------------

threading.Thread(target=run_flask).start()
threading.Thread(target=run_bot).start()
