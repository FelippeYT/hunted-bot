import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from playwright.async_api import async_playwright

# Tenta importar o modo stealth de forma segura para versões diferentes da lib
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

# --- FUNÇÃO DE SCRAPING COM BYPASS CLOUDFLARE ---
async def get_online_list():
    url = "https://rubinot.com.br/worlds/Tenebrium"
    api_url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
    
    async with async_playwright() as p:
        try:
            # Lançamento padrão (O Nixpacks cuidará do caminho)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            if stealth_async:
                await stealth_async(page)
            
            # 1. Abre a página e aguarda o desafio (aquela tela de 'Verificando' que você viu)
            print("⏳ Acessando site e aguardando verificação da Cloudflare...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 2. Espera 12 segundos para garantir que o desafio automático seja resolvido
            await asyncio.sleep(12) 
            
            # 3. Agora com o cookie de sessão, acessamos a API JSON
            await page.goto(api_url, wait_until="networkidle")
            
            content = await page.inner_text("body")
            data = json.loads(content)
            
            await browser.close()

            # Extração dos nomes do JSON
            players_list = []
            if isinstance(data, list):
                players_list = data
            elif isinstance(data, dict):
                players_list = data.get("players", data.get("data", []))

            return [p.get("name") for p in players_list if isinstance(p, dict) and p.get("name")]

        except Exception as e:
            print(f"❌ Erro no monitoramento: {e}")
            return []

# --- LOOP DE VERIFICAÇÃO ---
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

    # Detecção de Login
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            embed = discord.Embed(
                title="🟢 TARGET ONLINE",
                description=f"O alvo **{p}** está online no Rubinot!",
                color=0x2ecc71
            )
            await channel.send(embed=embed)

    # Detecção de Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(
                    title="🔴 TARGET OFFLINE",
                    description=f"O alvo **{p}** deslogou.",
                    color=0xe74c3c
                )
                await channel.send(embed=embed)

# --- COMANDOS DO DISCORD ---
@bot.event
async def on_ready():
    print(f"🔥 {bot.user} pronto para a caça!")
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
            print(f"📦 {len(tracked_players)} hunted players carregados.")
        except:
            pass
    
    if not check_loop.is_running():
        check_loop.start()

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** adicionado à lista de hunted.")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido da lista.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 Nenhum alvo na lista.")
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Lista de Alvos:**\n{lista}")
