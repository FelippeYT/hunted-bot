import discord
from discord.ext import commands, tasks
from playwright.async_api import async_playwright
from datetime import datetime
import json
import os
import asyncio
from gtts import gTTS

# ================= CONFIGURAÇÕES =================
TOKEN = "MTQ5MjAzMzMxODY1OTgyMTYxOQ.GCWike.9D6O8qGlZ5l86NBVdFS3O0Fko5JmCkBTTDF254"
CHANNEL_ID = 1492203477689176144
CHANNEL_FRIENDS = 1494019202053570621 # Novo canal friend log
FILE = "hunted_data.json"
FILE_FRIENDS = "friends_data.json"

AUTHORIZED_IDS = [
    315481947772157953,
    773068934630604800,
    192343484860989440,
    604349229984645149
]
# =================================================

# 1. DEFINIÇÃO DO BOT
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

hunted_players = {}  # { "Nome": level }
friend_players = {}  # { "Nome": level }
online_cache = set()
last_deaths_ids = set()

# --- FUNÇÕES AUXILIARES ---
async def get_api_data(url, endpoint_call):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="commit", timeout=60000)
            await asyncio.sleep(3) 
            data = await page.evaluate(f"async () => {{ const res = await fetch('{endpoint_call}'); return await res.json(); }}")
            await browser.close()
            return data
    except Exception as e:
        print(f"⚠️ Erro de Scrapping: {e}")
        return None

def save_hunted():
    with open(FILE, "w") as f:
        json.dump(hunted_players, f)

def save_friends():
    with open(FILE_FRIENDS, "w") as f:
        json.dump(friend_players, f)

# --- TAREFA 1: RADAR ONLINE E NÍVEIS ---
@tasks.loop(seconds=50)
async def radar_principal():
    global online_cache, hunted_players, friend_players
    ch_hunted = bot.get_channel(CHANNEL_ID)
    ch_friends = bot.get_channel(CHANNEL_FRIENDS)
    if not ch_hunted: return

    print("🔎 Radar: Verificando status e níveis...")
    data = await get_api_data("https://rubinot.com.br/worlds/Tenebrium", 
                              "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc")
    
    if data and 'players' in data:
        current_online_list = data['players']
        current_online_names = {p['name'] for p in current_online_list}
        
        for p in current_online_list:
            name = p['name']
            level = int(p['level'])

            # Verifica se é Hunted ou Friend
            is_hunted = name in hunted_players
            is_friend = name in friend_players

            if is_hunted or is_friend:
                target_channel = ch_hunted if is_hunted else ch_friends
                current_list = hunted_players if is_hunted else friend_players
                
                # 1. LOGIN
                if name not in online_cache:
                    online_cache.add(name)
                    title = "🟢 ALVO ONLINE" if is_hunted else "💎 AMIGO ONLINE"
                    color = discord.Color.green() if is_hunted else discord.Color.blue()
                    embed = discord.Embed(title=title, color=color)
                    embed.add_field(name="Nome", value=f"`{name}`", inline=True)
                    embed.add_field(name="Level", value=f"{level}", inline=True)
                    await target_channel.send(embed=embed)

                # 2. LEVEL MONITOR
                old_level = current_list.get(name, 0)
                if old_level != 0 and level != old_level:
                    diff = level - old_level
                    status = "📈 UP" if diff > 0 else "📉 DOWN"
                    color = discord.Color.blue() if diff > 0 else discord.Color.orange()
                    
                    embed = discord.Embed(title=f"{status}: Mudança de Level", color=color)
                    embed.add_field(name="Alvo" if is_hunted else "Amigo", value=f"`{name}`", inline=True)
                    embed.add_field(name="Novo Level", value=f"**{level}** (antes {old_level})", inline=True)
                    await target_channel.send(embed=embed)
                    
                    current_list[name] = level
                    save_hunted() if is_hunted else save_friends()
                elif old_level == 0:
                    current_list[name] = level
                    save_hunted() if is_hunted else save_friends()

        # 3. LOGOUT
        for name in list(online_cache):
            if name not in current_online_names:
                online_cache.remove(name)
                is_hunted = name in hunted_players
                is_friend = name in friend_players
                if is_hunted or is_friend:
                    target_channel = ch_hunted if is_hunted else ch_friends
                    title = "🔴 ALVO OFFLINE" if is_hunted else "💤 AMIGO OFFLINE"
                    embed = discord.Embed(title=title, color=discord.Color.light_grey())
                    embed.add_field(name="Nome", value=f"`{name}`", inline=False)
                    await target_channel.send(embed=embed)

# --- TAREFA 2: OBITUÁRIO (MORTES) ---
@tasks.loop(seconds=65)
async def check_mortes():
    global last_deaths_ids
    ch_hunted = bot.get_channel(CHANNEL_ID)
    ch_friends = bot.get_channel(CHANNEL_FRIENDS)
    if not ch_hunted: return

    print("💀 Cemitério: Lendo obituário...")
    data = await get_api_data("https://rubinot.com.br/deaths", 
                              "https://rubinot.com.br/api/deaths?world=21&page=1")
    
    if data and 'deaths' in data:
        for d in data['deaths']:
            player_name = d.get('victim')
            raw_time = d.get('time')
            death_id = f"{player_name}_{raw_time}"

            is_hunted = player_name in hunted_players
            is_friend = player_name in friend_players

            if (is_hunted or is_friend) and death_id not in last_deaths_ids:
                last_deaths_ids.add(death_id)
                target_channel = ch_hunted if is_hunted else ch_friends
                dt_object = datetime.fromtimestamp(int(raw_time))
                data_formatada = dt_object.strftime("%d/%m/%Y %H:%M:%S")
                
                killer_raw = d.get('killed_by', 'Desconhecido')
                killer = killer_raw.capitalize()
                
                is_player = d.get('is_player') == 1
                color = discord.Color.red() if is_player else discord.Color.dark_grey()
                tipo_morte = "⚔️ MORTE EM PVP" if is_player else "👹 MORTE PARA MONSTRO"

                embed = discord.Embed(title=f"{tipo_morte}", color=color, timestamp=dt_object)
                embed.set_thumbnail(url="https://i.imgur.com/Gz7ta92.gif")
                embed.add_field(name="👤 Vítima", value=f"`{player_name}`", inline=True)
                embed.add_field(name="📊 Nível", value=f"{d.get('level')}", inline=True)
                embed.add_field(name="💀 Causa", value=f"**{killer}**", inline=False)
                
                most_dmg = d.get('mostdamage_by')
                if most_dmg and most_dmg != killer_raw:
                    embed.add_field(name="🎯 Maior Dano", value=most_dmg.capitalize(), inline=True)
                
                embed.set_footer(text=f"Horário: {data_formatada}")
                await target_channel.send(embed=embed)

        if len(last_deaths_ids) > 150:
            last_deaths_ids = set(list(last_deaths_ids)[-100:])

# --- COMANDOS ---
@bot.command()
async def add(ctx, *, name: str):
    if name not in hunted_players:
        hunted_players[name] = 0
        save_hunted()
        await ctx.send(f"🎯 `{name}` adicionado à lista de alvos.")

@bot.command()
async def remove(ctx, *, name: str):
    if name in hunted_players:
        del hunted_players[name]
        save_hunted()
        await ctx.send(f"🕊️ `{name}` removido.")

@bot.command(aliases=['list'])
async def lista(ctx):
    if not hunted_players: return await ctx.send("Lista vazia.")
    msg = "**💀 Monitorando:**\n" + "\n".join([f"- {p} (Lvl: {v})" for p, v in hunted_players.items()])
    await ctx.send(msg)

# --- NOVOS COMANDOS FRIENDS ---
@bot.command()
async def friend(ctx, *, name: str):
    if name not in friend_players:
        friend_players[name] = 0
        save_friends()
        await ctx.send(f"💎 `{name}` adicionado à lista de amigos.")

@bot.command()
async def unfriend(ctx, *, name: str):
    if name in friend_players:
        del friend_players[name]
        save_friends()
        await ctx.send(f"👋 `{name}` removido da lista de amigos.")

@bot.command()
async def friends(ctx):
    if not friend_players: return await ctx.send("Lista de amigos vazia.")
    msg = "**💎 Amigos Monitorados:**\n" + "\n".join([f"- {p} (Lvl: {v})" for p, v in friend_players.items()])
    await ctx.send(msg)

# --- COMANDO DO MASS PUSH ---
@bot.command()
async def masspush(ctx):
    if ctx.author.id not in AUTHORIZED_IDS:
        return await ctx.send("❌ Você não tem permissão.")
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("⚠️ Entre em um canal de voz primeiro!")

    dest = ctx.author.voice.channel
    await ctx.send(f"Puxando todos os membros para `{dest.name}`...")
    count = 0
    for channel in ctx.guild.voice_channels:
        if channel == dest: continue
        for member in channel.members:
            try:
                await member.move_to(dest)
                count += 1
                await asyncio.sleep(0.1)
            except: pass
    await ctx.send(f"✅ `{count}` membros movidos.")

# --- INICIALIZAÇÃO ---
@bot.event
async def on_ready():
    global hunted_players, friend_players
    print(f"✅ Bot Online: {bot.user}")
    
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            data = json.load(f)
            hunted_players = data if isinstance(data, dict) else {n: 0 for n in data}
    
    if os.path.exists(FILE_FRIENDS):
        with open(FILE_FRIENDS, "r") as f:
            data = json.load(f)
            friend_players = data if isinstance(data, dict) else {n: 0 for n in data}

    if not radar_principal.is_running(): radar_principal.start()
    if not check_mortes.is_running(): check_mortes.start()

@bot.command()
async def masspoke(ctx, *, mensagem: str):
    # 1. Verificação de permissão
    if ctx.author.id not in AUTHORIZED_IDS:
        return await ctx.send("❌ Sem permissão.")

    await ctx.send(f"📢 Iniciando Mass Poke com a mensagem: `{mensagem}`")

    # 2. Gerar o áudio uma única vez antes de começar o loop
    try:
        tts = gTTS(text=mensagem, lang='pt', tld='com.br')
        tts.save("mass_poke.mp3")
    except Exception as e:
        return await ctx.send(f"❌ Erro ao gerar áudio: {e}")

    # 3. Percorrer todos os canais de voz que têm alguém dentro
    for channel in ctx.guild.voice_channels:
        if len(channel.members) == 0:
            continue # Pula salas vazias

        try:
            # Conecta à sala
            vc = await channel.connect()
            
            # Toca a mensagem
            vc.play(discord.FFmpegPCMAudio("mass_poke.mp3"))

            # Aguarda o áudio terminar
            while vc.is_playing():
                await asyncio.sleep(0.5)

            # Desconecta e espera um pouco antes da próxima sala
            await vc.disconnect()
            await asyncio.sleep(1) 

        except Exception as e:
            print(f"Erro ao entrar na sala {channel.name}: {e}")
            # Garante que desconectou se houver erro
            if ctx.voice_client:
                await ctx.voice_client.disconnect()

    await ctx.send("✅ O Mass Poke foi finalizado em todas as salas!")

bot.run(TOKEN)