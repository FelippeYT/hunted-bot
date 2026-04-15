import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
# Sua chave do ScraperAnt
ANT_KEY = "aa857e69e13643f58fca0f11945532c547a8e11d590"
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players_cache = set()

def get_online_list():
    target_url = "https://rubinot.com.br/worlds/Tenebrium"
    # Configuração para o ScraperAnt resolver o JS e a Cloudflare
    api_url = f"https://api.scraperant.com/v2/general?url={target_url}&x-api-key={ANT_KEY}&browser=true"
    
    try:
        print("📡 [ANT] Solicitando página via Proxy...")
        response = requests.get(api_url, timeout=60)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            names = []

            # Varre o HTML processado em busca dos links de personagens
            for link in soup.find_all('a', href=True):
                if '/character/' in link['href']:
                    name = link.text.strip()
                    if name and name not in names:
                        names.append(name)
            
            print(f"✅ [ANT] Sucesso! {len(names)} players encontrados.")
            return names
        else:
            print(f"❌ [ANT] Erro {response.status_code}: {response.text[:100]}")
            return []
    except Exception as e:
        print(f"❌ [ANT] Falha na conexão: {e}")
        return []

@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    # Roda a função de rede
    current_online = await bot.loop.run_in_executor(None, get_online_list)
    current_online_set = set(current_online)

    # Detecção de Login
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            await channel.send(f"🟢 **LOGIN:** `{p}`")

    # Detecção de Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                await channel.send(f"🔴 **LOGOUT:** `{p}`")

@bot.event
async def on_ready():
    print(f"🔥 Bikini Bottom Hunted via ScraperAnt ON!")
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
            print(f"📦 {len(tracked_players)} alvos carregados.")
        except: pass
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
        return await ctx.send("📭 Lista vazia.")
    lista = "\n".join([f"- {p}" for p in tracked_players])
    await ctx.send(f"💀 **Hunted List:**\n{lista}")

if __name__ == "__main__":
    bot.run(TOKEN)
