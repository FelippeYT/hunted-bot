import os
# Configura o caminho do navegador ANTES de importar o playwright
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/app/pw-browsers'

import discord
from discord.ext import commands, tasks
import json
import asyncio
from playwright.async_api import async_playwright

# Tenta importar o modo stealth de forma segura
try:
    from playwright_stealth import stealth_async
except ImportError:
    try:
        from playwright_stealth import stealth as stealth_async
    except:
        stealth_async = None

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players_cache = set()

# --- FUNÇÃO DE SCRAPING ---
async def get_online_list():
    url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
    
    async with async_playwright() as p:
        try:
            # Lança o navegador usando o caminho configurado
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Ativa o modo furtivo se a lib estiver disponível
            if stealth_async:
                await stealth_async(page)
            
            # 1. Visita a página principal para validar cookies (Bypass Cloudflare)
            await page.goto("https://rubinot.com.br/worlds/Tenebrium", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3) # Espera o desafio de JS carregar
            
            # 2. Acessa a API
            await page.goto(url, wait_until="networkidle")
            
            # 3. Extrai o JSON
            content = await page.inner_text("body")
            data = json.loads(content)
            
            await browser.close()

            # Processa a lista de jogadores
            players_list = []
            if isinstance(data, list):
                players_list = data
            elif isinstance(data, dict):
                players_list = data.get("players", data.get("data", []))

            return [p.get("name") for p in players_list if isinstance(p, dict) and p.get("name")]

        except Exception as e:
            print(f"❌ Erro Playwright: {e}")
            return []

# --- LOOP DE MONITORAMENTO ---
@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    current_online = await get_online_list()
    if not current_online and not online_players_cache:
        return

    current_online_set = set(current_online)

    # Lógica de Login
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            embed = discord.Embed(
                title="🟢 ONLINE",
                description=f"O alvo **{p}** foi detectado no jogo!",
                color=0x2ecc71
            )
            await channel.send(embed=embed)

    # Lógica de Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(
                    title="🔴 OFFLINE",
                    description=f"O alvo **{p}** saiu do jogo.",
                    color=0xe74c3c
                )
                await channel.send(embed=embed)

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f"🔥 {bot.user} Online com Caminho Customizado!")
    # Carrega alvos salvos
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
            print(f"📦 {len(tracked_players)} alvos carregados.")
        except:
            pass
    
    if not check_loop.is_running():
        check_loop.start()

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** adicionado à lista de hunteds.")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido da lista.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 A lista está vazia.")
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Lista de Hunted:**\n{lista}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Token do Discord não configurado!")
