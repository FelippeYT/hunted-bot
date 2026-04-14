import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players_cache = set()

# --- SCRAPER COM STEALTH ---
async def get_online_list():
    url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Aplica o modo Stealth para esconder que é um bot
            await stealth_async(page)
            
            # Navega até a página principal primeiro para pegar o cookie da Cloudflare
            await page.goto("https://rubinot.com.br/worlds/Tenebrium", wait_until="networkidle")
            
            # Agora tenta acessar a API
            await page.goto(url)
            
            # Pega o conteúdo (JSON) que aparece na tela
            content = await page.inner_text("body")
            data = json.loads(content)
            
            await browser.close()

            players_list = data.get("players", data.get("data", [])) if isinstance(data, dict) else data
            return [p.get("name") for p in players_list if isinstance(p, dict) and p.get("name")]

        except Exception as e:
            print(f"❌ Erro Playwright: {e}")
            return []

# --- LOOP E COMANDOS ---
@tasks.loop(seconds=60) # Aumentei para 60s para não sobrecarregar o Railway
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    current_online = await get_online_list()
    if not current_online and not online_players_cache: return

    current_online_set = set(current_online)

    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            await channel.send(f"🟢 **LOGIN:** `{p}`")

    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                await channel.send(f"🔴 **LOGOUT:** `{p}`")

@bot.event
async def on_ready():
    print(f"🔥 {bot.user} Online com Stealth!")
    if os.path.exists(FILE):
        with open(FILE, "r") as f: tracked_players.update(json.load(f))
    check_loop.start()

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)
    with open(FILE, "w") as f: json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 {name} na mira.")

bot.run(TOKEN)
