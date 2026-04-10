import discord
from discord.ext import commands, tasks
from playwright.sync_api import sync_playwright
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
# PLAYWRIGHT
# ========================

def get_online_players():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://rubinot.com.br/worlds/Tenebrium", timeout=60000)

            # espera a tabela carregar
            page.wait_for_selector("table tbody tr", timeout=30000)

            players = page.query_selector_all("table tbody tr")

            names = []

            for row in players:
                name = row.query_selector("td a")
                if name:
                    names.append(name.inner_text())

            browser.close()
            return names

    except Exception as e:
        print("Erro scraping:", e)
        return []

# ========================
# READY
# ========================

@bot.event
async def on_ready():
    global last_online

    print(f"🔥 Bot online: {bot.user}")

    last_online = set(get_online_players())
    check_online.start()

# ========================
# LOOP
# ========================

@tasks.loop(seconds=60)
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
# COMMANDS
# ========================

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    save_players()
    await ctx.send(f"✅ {name} adicionado")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    save_players()
    await ctx.send(f"❌ {name} removido")

@bot.command()
async def list(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player.")
    else:
        await ctx.send("\n".join(tracked_players))

# ========================
# START
# ========================

bot.run(TOKEN)
