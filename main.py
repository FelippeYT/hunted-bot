import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import asyncio

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cria o scraper que simula um navegador real
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

tracked_players = set()
online_players_cache = set()

# --- MOTOR DE EXTRAÇÃO (HTML SCRAPING) ---
def get_online_list():
    url = "https://rubinot.com.br/worlds/Tenebrium"
    try:
        # Pega o HTML da página (onde os dados já estão processados)
        response = scraper.get(url, timeout=20)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            names = []

            # Procura por links que apontam para o perfil dos personagens
            # O RubinOT usa o padrão href="/character/NomeDoPlayer"
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/character/' in href:
                    # O texto do link é o nome do player
                    name = link.text.strip()
                    if name and name not in names:
                        names.append(name)
            
            print(f"📡 [SCRAPER] {len(names)} players encontrados na página.")
            return names
        else:
            print(f"⚠️ [SCRAPER] Erro HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ [SCRAPER] Erro ao ler HTML: {e}")
        return []

# --- LOOP DE MONITORAMENTO ---
@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    # Executa a função síncrona em uma thread separada para não travar o bot
    current_online = await bot.loop.run_in_executor(None, get_online_list)
    
    if not current_online and not online_players_cache:
        return

    current_online_set = set(current_online)

    # Detecção de Logins
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            embed = discord.Embed(
                title="🟢 TARGET ONLINE",
                description=f"**{p}** foi detectado no visual do site!",
                color=0x2ecc71
            )
            await channel.send(embed=embed)

    # Detecção de Logouts
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(
                    title="🔴 TARGET OFFLINE",
                    description=f"**{p}** sumiu da lista visual.",
                    color=0xe74c3c
                )
                await channel.send(embed=embed)

# --- COMANDOS DO BOT ---
@bot.event
async def on_ready():
    print(f"🔥 {bot.user} Online (Modo Visual HTML)!")
    
    # Carrega a lista de alvos
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
    await ctx.send(f"🎯 **{name}** adicionado à caça.")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 Lista de alvos vazia.")
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Alvos Atuais:**\n{lista}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERRO: DISCORD_TOKEN não configurado!")
