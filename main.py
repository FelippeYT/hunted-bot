import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import json
import os

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
ANT_KEY = "aa857e69e13643f58fca0f11945532c547a8e11d590"
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players_cache = set()

def get_online_list():
    target_url = "https://rubinot.com.br/worlds/Tenebrium"
    api_url = "https://api.scraperant.com/v2/general"
    
    params = {
        'url': target_url,
        'x-api-key': ANT_KEY,
        'browser': 'true',
        'wait_for_selector': 'a[href*="/character/"]' 
    }
    
    try:
        print("📡 [ANT] Solicitando página...")
        response = requests.get(api_url, params=params, timeout=60)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            names = []
            for link in soup.find_all('a', href=True):
                if '/character/' in link['href']:
                    name = link.get_text(strip=True)
                    if name and name not in names:
                        names.append(name)
            return names
        return []
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return []

@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    current_online = await bot.loop.run_in_executor(None, get_online_list)
    current_online_set = set(current_online)

    # Logins
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            await channel.send(f"🟢 **LOGIN:** `{p}`")

    # Logouts
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                await channel.send(f"🔴 **LOGOUT:** `{p}`")

@bot.event
async def on_ready():
    print(f"🔥 Bot Online! Aguardando comando !start_hunt")
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
        except: pass

# --- NOVOS COMANDOS DE CONTROLE ---

@bot.command()
async def start_hunt(ctx):
    if not check_loop.is_running():
        check_loop.start()
        await ctx.send("⚔️ **Monitoramento INICIADO.** Gastando créditos do ScraperAnt...")
    else:
        await ctx.send("⚠️ O monitoramento já está em execução.")

@bot.command()
async def stop_hunt(ctx):
    if check_loop.is_running():
        check_loop.stop()
        online_players_cache.clear() # Limpa o cache para não bugar na próxima vez
        await ctx.send("🛡️ **Monitoramento PARADO.** Créditos poupados.")
    else:
        await ctx.send("⚠️ O monitoramento já estava desligado.")

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** adicionado.")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido.")

@bot.command()
async def hunted(ctx):
    lista = "\n".join([f"- {p}" for p in tracked_players]) if tracked_players else "Vazia"
    await ctx.send(f"💀 **Alvos:**\n{lista}\n\n*Status: {'✅ Ativo' if check_loop.is_running() else '❌ Pausado'}*")

if __name__ == "__main__":
    bot.run(TOKEN)
