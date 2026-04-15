import os
import discord
from discord.ext import commands, tasks
import json
import asyncio
from playwright.async_api import async_playwright

# Define o caminho para a pasta local que criamos no nixpacks
# O ponto '.' refere-se ao diretório atual do projeto no Railway (/app)
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(os.getcwd(), 'browser-data')

# Tenta importar o modo stealth
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

# --- FUNÇÃO DE SCRAPING (O MOTOR DO BOT) ---
async def get_online_list():
    url = "https://rubinot.com.br/worlds/Tenebrium"
    api_url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
    
    async with async_playwright() as p:
        browser = None
        try:
            print("🚀 [SCRAPER] Iniciando Chromium...")
            # Args extras para rodar melhor no ambiente Linux do Railway
            browser = await p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            if stealth_async:
                await stealth_async(page)
            
            print("⏳ [SCRAPER] Acessando site e aguardando Cloudflare (15s)...")
            # Entra na página e espera carregar o básico
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # O tempo que você viu no celular: esperando o desafio ser resolvido
            await asyncio.sleep(15) 
            
            print("📡 [SCRAPER] Solicitando API de jogadores...")
            # Agora tenta acessar o JSON
            await page.goto(api_url, wait_until="networkidle", timeout=30000)
            
            content = await page.inner_text("body")
            
            # Validação: Se começar com <!, é HTML (bloqueio), não JSON.
            if content.strip().startswith("<!DOCTYPE") or "Cloudflare" in content:
                print("⚠️ [SCRAPER] Bloqueio detectado: Recebi HTML em vez de JSON.")
                return []

            data = json.loads(content)
            print("✅ [SCRAPER] Dados obtidos com sucesso!")
            
            # Extração segura
            players_list = []
            if isinstance(data, list):
                players_list = data
            elif isinstance(data, dict):
                players_list = data.get("players", data.get("data", []))

            return [p.get("name") for p in players_list if isinstance(p, dict) and p.get("name")]

        except Exception as e:
            print(f"❌ [SCRAPER] Erro crítico: {e}")
            return []
        finally:
            if browser:
                await browser.close()
                print("🔒 [SCRAPER] Browser fechado.")

# --- LOOP DE MONITORAMENTO ---
@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("⚠️ [SISTEMA] Canal não encontrado. Verifique o CHANNEL_ID.")
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
                title="🟢 TARGET ONLINE",
                description=f"O alvo **{p}** entrou no jogo!",
                color=0x2ecc71
            )
            await channel.send(embed=embed)

    # Lógica de Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(
                    title="🔴 TARGET OFFLINE",
                    description=f"O alvo **{p}** saiu do jogo.",
                    color=0xe74c3c
                )
                await channel.send(embed=embed)

# --- COMANDOS E INICIALIZAÇÃO ---
@bot.event
async def on_ready():
    print(f"🔥 {bot.user} pronto para a caça!")
    # Carregar alvos salvos
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
            print(f"📦 {len(tracked_players)} alvos carregados do arquivo.")
        except:
            pass
    
    if not check_loop.is_running():
        check_loop.start()

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** agora está sendo monitorado!")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido da lista.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 Lista vazia.")
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Alvos Atuais:**\n{lista}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERRO: DISCORD_TOKEN não encontrado nas variáveis do Railway!")
