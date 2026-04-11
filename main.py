import discord
from discord.ext import commands, tasks
from playwright.async_api import async_playwright
import asyncio
import json
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FILE = "players.json"
tracked_players = set()
online_players = set()


# ---------------- LOAD / SAVE ----------------

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


# ---------------- SCRAPER ----------------

async def fetch_html():
    url = "https://rubinot.com.br/worlds/Tenebrium"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
        )

        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")

        html = await page.content()

        await browser.close()

        return html


def parse_players(html):
    players = []

    for line in html.split("\n"):
        if "/characters?name=" in line:
            try:
                start = line.find("name=") + 5
                end = line.find('"', start)
                name = line[start:end].replace("%20", " ")

                if name:
                    players.append(name)
            except:
                pass

    return list(set(players))


# ---------------- DISCORD ----------------

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

@bot.command()
async def untrack(ctx, *, name):
    tracked_players.discard(name)
    save_players()
    await ctx.send(f"❌ {name} removido")

@bot.command(name="list")
async def list_cmd(ctx):
    if not tracked_players:
        await ctx.send("📭 Nenhum player")
    else:
        await ctx.send("\n".join(tracked_players))


# ---------------- LOOP ----------------

@tasks.loop(seconds=60)
async def check_players():
    global online_players

    html = await fetch_html()
    players = parse_players(html)

    for p in players:
        if p in tracked_players and p not in online_players:
            online_players.add(p)
            await notify(f"🟢 {p} entrou no jogo!")

    for p in list(online_players):
        if p not in players:
            online_players.remove(p)
            await notify(f"🔴 {p} saiu do jogo!")


# ---------------- NOTIFY ----------------

async def notify(msg):
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(msg)
                return


bot.run(TOKEN)
