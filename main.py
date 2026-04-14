import discord
from discord.ext import commands, tasks
import json
import os
import cloudscraper
from bs4 import BeautifulSoup
import asyncio

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
# ID do canal onde o bot enviará os alertas de hunted
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0)) 
FILE = "players.json"

# --- SETUP DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Criamos o scraper globalmente para manter cookies/sessão
scraper = cloudscraper.create_scraper()

tracked_players = set()
online_players_cache = set()

# --- PERSISTÊNCIA DE DADOS ---
def load_data():
    global tracked_players
    if os.path.exists(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                tracked_players = set(json.load(f))
            print(f"📦 {len(tracked_players)} players carregados da lista.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar arquivo: {e}")

def save_data():
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(list(tracked_players), f, indent=4)
    except Exception as e:
        print(f"⚠️ Erro ao salvar arquivo: {e}")

# --- LÓGICA DO SCRAPER (RUBINOT) ---
def get_online_list():
    url = "https://rubinot.com.br/worlds/Tenebrium"
    try:
        # Simula um navegador real para evitar bloqueios
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = scraper.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Erro no site: Status {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        players = []
        
        # Busca links que levam para a página de personagens (padrão de OTServers)
        for link in soup.find_all("a", href=True):
            if "characters?name=" in link["href"]:
                name = link.get_text().strip()
                if name:
                    players.append(name)
        
        return list(set(players))
    except Exception as e:
        print(f"❌ Falha no scraping: {e}")
        return []

# --- COMANDOS DISCORD ---
@bot.event
async def on_ready():
    print(f"🔥 Bot Hunted {bot.user} está ONLINE!")
    load_data()
    if not check_loop.is_running():
        check_loop.start()

@bot.command(name="track")
async def track(ctx, *, name: str):
    """Adiciona um player à lista de monitoramento"""
    tracked_players.add(name)
    save_data()
    await ctx.send(f"🎯 **{name}** agora é um alvo monitorado!")

@bot.command(name="untrack")
async def untrack(ctx, *, name: str):
    """Remove um player da lista"""
    tracked_players.discard(name)
    save_data()
    await ctx.send(f"🕊️ **{name}** foi removido da lista.")

@bot.command(name="hunted")
async def list_hunted(ctx):
    """Lista todos os players que estão sendo monitorados"""
    if not tracked_players:
        return await ctx.send("📭 A lista de hunted está vazia.")
    
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Lista de Hunted:**\n{lista}")

# --- LOOP DE MONITORAMENTO ---
@tasks.loop(seconds=40)
async def check_loop():
    global online_players_cache
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    current_online = get_online_list()
    if not current_online and not online_players_cache:
        return

    current_online_set = set(current_online)

    # Verifica quem LOGOU
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            embed = discord.Embed(
                title="🟢 TARGET ONLINE",
                description=f"O player **{p}** acabou de entrar no jogo!",
                color=0x2ecc71
            )
            await channel.send(embed=embed)

    # Verifica quem LOGOU OUT
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(
                    title="🔴 TARGET OFFLINE",
                    description=f"O player **{p}** saiu do jogo.",
                    color=0xe74c3c
                )
                await channel.send(embed=embed)

# Iniciar o bot
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERRO: DISCORD_TOKEN não encontrado nas variáveis de ambiente.")
