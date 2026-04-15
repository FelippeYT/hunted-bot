import discord
from discord.ext import commands, tasks
import requests
import json
import os

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
# Chave do ScraperAnt (deixada no código conforme sua preferência)
ANT_KEY = "aa857e69e13643f58fca0f11945532c547a8e11d590"
FILE = "players.json"

# URLs
TARGET_API = "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc"
SCRAPERANT_URL = "https://api.scraperant.com/v2/general"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()
online_players_cache = set()

def get_online_list():
    """Consulta a API oculta do RubinOT via ScraperAnt"""
    params = {
        'url': TARGET_API,
        'x-api-key': ANT_KEY,
        'browser': 'false', # Tenta modo rápido/barato primeiro
    }
    
    # Fingindo que a chamada vem de dentro do site oficial
    headers = {
        "Referer": "https://rubinot.com.br/worlds/Tenebrium"
    }
    
    try:
        print("📡 [ANT] Consultando API do RubinOT...")
        response = requests.get(SCRAPERANT_URL, params=params, headers=headers, timeout=30)
        
        # Se o modo barato falhar (403), tenta o modo navegador (mais potente)
        if response.status_code == 403:
            print("⚠️ [ANT] Acesso negado no modo rápido. Tentando com modo Navegador...")
            params['browser'] = 'true'
            response = requests.get(SCRAPERANT_URL, params=params, timeout=60)

        if response.status_code == 200:
            data = response.json()
            # Extrai apenas os nomes da lista de jogadores
            names = [p['name'] for p in data.get('players', [])]
            print(f"✅ [ANT] Sucesso! {len(names)} players capturados.")
            return names
        else:
            print(f"❌ [ANT] Erro HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ [ANT] Erro na requisição: {e}")
        return []

@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: 
        print("❌ CHANNEL_ID não configurado corretamente.")
        return

    # Executa a busca (em thread separada para não travar o bot)
    current_online = await bot.loop.run_in_executor(None, get_online_list)
    current_online_set = set(current_online)

    if not current_online_set:
        return

    # Logica de Login
    for p in current_online_set:
        if p in tracked_players and p not in online_players_cache:
            online_players_cache.add(p)
            await channel.send(f"🟢 **LOGIN:** `{p}`")

    # Logica de Logout
    for p in list(online_players_cache):
        if p not in current_online_set:
            online_players_cache.remove(p)
            if p in tracked_players:
                await channel.send(f"🔴 **LOGOUT:** `{p}`")

@bot.event
async def on_ready():
    print(f"🔥 Bot via API ScraperAnt Online!")
    print(f"Comandos: !start_hunt / !stop_hunt")
    
    # Carrega alvos salvos
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                saved = json.load(f)
                tracked_players.update(saved)
            print(f"📦 {len(tracked_players)} alvos carregados do arquivo.")
        except: pass

# --- COMANDOS ---

@bot.command()
async def start_hunt(ctx):
    if not check_loop.is_running():
        check_loop.start()
        await ctx.send("⚔️ **Monitoramento INICIADO.** A caça começou!")
    else:
        await ctx.send("⚠️ O bot já está caçando.")

@bot.command()
async def stop_hunt(ctx):
    if check_loop.is_running():
        check_loop.stop()
        online_players_cache.clear()
        await ctx.send("🛡️ **Monitoramento PARADO.** Créditos poupados.")
    else:
        await ctx.send("⚠️ O bot já estava em repouso.")

@bot.command()
async def track(ctx, *, name: str):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** adicionado à Hunted List.")

@bot.command()
async def untrack(ctx, *, name: str):
    tracked_players.discard(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🕊️ **{name}** removido da lista.")

@bot.command()
async def hunted(ctx):
    if not tracked_players:
        return await ctx.send("📭 A lista de alvos está vazia.")
    
    lista = "\n".join([f"- {p}" for p in tracked_players])
    status = "✅ ATIVO" if check_loop.is_running() else "❌ PAUSADO"
    await ctx.send(f"💀 **Hunted List:**\n{lista}\n\n*Status: {status}*")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Erro: DISCORD_TOKEN não encontrado nas variáveis de ambiente.")
    else:
        bot.run(TOKEN)
