import discord
from discord.ext import commands, tasks
import json
import os
import cloudscraper
import asyncio

# --- CONFIGURAÇÕES VIA VARIÁVEIS DE AMBIENTE ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
FILE = "players.json"

# --- SETUP DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Criamos o scraper com um navegador padrão para passar pela Cloudflare
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

tracked_players = set()
online_players_cache = set()

# --- PERSISTÊNCIA ---
def load_data():
    global tracked_players
    if os.path.exists(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                tracked_players = set(json.load(f))
            print(f"📦 {len(tracked_players)} players na lista de hunted.")
        except:
            tracked_players = set()

def save_data():
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(list(tracked_players), f, indent=4)
    except Exception as e:
        print(f"⚠️ Erro ao salvar arquivo: {e}")

# --- SCRAPER DA API (O PULO DO GATO) ---
def get_online_list():
    # URL da API do Next.js que você encontrou
    api_url = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
    
    headers = {
        "accept": "*/*",
        "accept-language": "pt-BR,pt;q=0.9",
        "sec-ch-ua": '"Chromium";v="123", "Not:A-Brand";v="8"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin", # Essencial para APIs Next.js
        "referrer": "https://rubinot.com.br/worlds/Tenebrium",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    try:
        response = scraper.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Tentamos extrair a lista de players conforme a estrutura comum de APIs
            # Se a API retornar um objeto com 'players', usamos ele. Se for lista direta, usamos data.
            players_list = []
            if isinstance(data, list):
                players_list = data
            elif isinstance(data, dict):
                # Tenta caminhos comuns (ajuste se o print do JSON mostrar outro caminho)
                players_list = data.get("players", data.get("data", []))
            
            # Extrai apenas os nomes
            names = [p.get("name") for p in players_list if isinstance(p, dict) and p.get("name")]
            return names
        
        else:
            print(f"❌ Erro API ({response.status_code}). Cloudflare pode ter bloqueado.")
            return []
            
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return []

# --- COMANDOS ---
@bot.event
async def on_ready():
    print(f"🔥 {bot.user} Online!")
    load_data()
    if not check_loop.is_running():
        check_loop.start()

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    save_data()
    await ctx.send(f"🎯 **{name}** agora está na lista de monitoramento!")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    save_data()
    await ctx.send(f"🕊️ **{name}** foi removido da lista.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 Ninguém na lista.")
    await ctx.send(f"💀 **Alvos Atuais:**\n" + "\n".join([f"- {p}" for p in tracked_players]))

# --- LOOP ---
@tasks.loop(seconds=35) # Intervalo seguro para não cansar a API
async def check_loop():
    global online_players_cache
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    current_online = get_online_list()
    if not current_online and not online_players_cache:
        return

    current_online_set = set(current_online)

    # Detectar Login
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            embed = discord.Embed(title="🟢 TARGET ONLINE", description=f"O alvo **{p}** entrou!", color=0x2ecc71)
            await channel.send(embed=embed)

    # Detectar Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                embed = discord.Embed(title="🔴 TARGET OFFLINE", description=f"O alvo **{p}** saiu.", color=0xe74c3c)
                await channel.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
