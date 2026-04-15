import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import json
import os

# --- CONFIGURAÇÕES ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
FILE = "players.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Scraper configurado para parecer um Chrome real de Windows
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

tracked_players = set()
online_players_cache = set()

def get_online_list():
    url = "https://rubinot.com.br/worlds/Tenebrium"
    try:
        # Tenta baixar o visual da página
        response = scraper.get(url, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            names = []

            # Varre todos os links. Se o nome estiver na tela, ele é um link de personagem
            for link in soup.find_all('a', href=True):
                if '/character/' in link['href']:
                    name = link.text.strip()
                    if name and name not in names:
                        names.append(name)
            
            # Log para você acompanhar no Railway
            if names:
                print(f"✅ [SUCESSO] {len(names)} players lidos do visual.")
            else:
                print("⚠️ [AVISO] Página lida, mas nenhum nome encontrado. O site pode ser 100% JS.")
            
            return names
        else:
            print(f"❌ [ERRO] Status {response.status_code}. Cloudflare bloqueou o acesso.")
            return []
    except Exception as e:
        print(f"❌ [ERRO] Falha na conexão: {e}")
        return []

@tasks.loop(seconds=60)
async def check_loop():
    global online_players_cache
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    # Roda a função de rede
    current_online = await bot.loop.run_in_executor(None, get_online_list)
    current_online_set = set(current_online)

    # Lógica de Notificação
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
    print(f"🔥 Bikini Bottom Hunted ON (Modo Visual)!")
    if os.path.exists(FILE):
        try:
            with open(FILE, "r") as f:
                tracked_players.update(json.load(f))
        except: pass
    if not check_loop.is_running():
        check_loop.start()

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)
    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)
    await ctx.send(f"🎯 **{name}** adicionado.")

@bot.command()
async def hunted(ctx):
    lista = "\n".join(tracked_players) if tracked_players else "Vazia"
    await ctx.send(f"💀 **Hunted List:**\n{lista}")

if __name__ == "__main__":
    bot.run(TOKEN)
