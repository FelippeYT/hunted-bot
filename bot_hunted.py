import discord
from discord.ext import commands, tasks
from playwright.async_api import async_playwright
from datetime import datetime
import json
import os
import asyncio
from gtts import gTTS

# ================= CONFIGURAÇÕES =================
TOKEN = ""
CHANNEL_ID = 
CHANNEL_FRIENDS = 
FILE = "hunted_data.json"
FILE_FRIENDS = "friends_data.json"
WEB_JSON = "monitor_data.json" 

AUTHORIZED_IDS = [

]

browser_instance = None
file_lock = asyncio.Lock()
# =================================================

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

hunted_players = {}  
friend_players = {}  
online_cache = set()
last_deaths_ids = set()
web_events = []

async def update_web_json(name, level, event_type, details, status, manual_datetime=None):
    global web_events
    async with file_lock:
        if not isinstance(web_events, list): web_events = []
        dt_string = manual_datetime if manual_datetime else datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        p_type = "friend" if name in friend_players else "hunted" if name in hunted_players else "unknown"
        
        new_event = {
            "datetime": dt_string,
            "name": name, "level": level, "event": event_type, 
            "details": details, "status": status, "player_type": p_type
        }
        web_events.append(new_event)
        try:
            web_events.sort(key=lambda x: datetime.strptime(x['datetime'], "%d/%m/%Y %H:%M:%S"), reverse=True)
        except: pass
        web_events = web_events[:100] 
        with open(WEB_JSON, "w", encoding="utf-8") as f:
            json.dump(web_events, f, ensure_ascii=False, indent=4)

async def get_api_data(url, endpoint_call):
    global browser_instance
    try:
        if not browser_instance:
            p = await async_playwright().start()
            browser_instance = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        
        context = await browser_instance.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="commit", timeout=60000)
        await asyncio.sleep(2) 
        data = await page.evaluate(f"async () => {{ const res = await fetch('{endpoint_call}'); return await res.json(); }}")
        await page.close()
        await context.close()
        return data
    except Exception as e:
        print(f"⚠️ Erro de Scrapping: {e}")
        return None

def save_hunted():
    with open(FILE, "w") as f: json.dump(hunted_players, f)

def save_friends():
    with open(FILE_FRIENDS, "w") as f: json.dump(friend_players, f)

@tasks.loop(seconds=50)
async def radar_principal():
    global online_cache, hunted_players, friend_players
    ch_hunted = bot.get_channel(CHANNEL_ID)
    ch_friends = bot.get_channel(CHANNEL_FRIENDS)
    if not ch_hunted: return

    data = await get_api_data("https://rubinot.com.br/worlds/Tenebrium", 
                              "https://rubinot.com.br/api/worlds/Tenebrium?order=name_asc")
    
    if data and 'players' in data:
        current_online_names = {p['name'] for p in data['players']}
        for p in data['players']:
            name, level = p['name'], int(p['level'])
            is_hunted, is_friend = name in hunted_players, name in friend_players

            if is_hunted or is_friend:
                target_channel = ch_hunted if is_hunted else ch_friends
                current_list = hunted_players if is_hunted else friend_players
                
                if name not in online_cache:
                    online_cache.add(name)
                    await update_web_json(name, level, "status", "Entrou no jogo", "on")
                    title = "🟢 ALVO ONLINE" if is_hunted else "💎 AMIGO ONLINE"
                    embed = discord.Embed(title=title, color=discord.Color.green() if is_hunted else discord.Color.blue())
                    embed.add_field(name="Nome", value=f"`{name}`", inline=True)
                    embed.add_field(name="Level", value=f"{level}", inline=True)
                    await target_channel.send(embed=embed)

                old_level = current_list.get(name, 0)
                if old_level != 0 and level != old_level:
                    diff = level - old_level
                    status = "📈 UP" if diff > 0 else "📉 DOWN"
                    await update_web_json(name, level, "up" if diff > 0 else "down", f"{status} (antes {old_level})", "on")
                    embed = discord.Embed(title=f"{status}: Mudança de Level", color=discord.Color.blue() if diff > 0 else discord.Color.orange())
                    embed.add_field(name="Alvo" if is_hunted else "Amigo", value=f"`{name}`", inline=True)
                    embed.add_field(name="Novo Level", value=f"**{level}** (antes {old_level})", inline=True)
                    await target_channel.send(embed=embed)
                    current_list[name] = level
                    save_hunted() if is_hunted else save_friends()
                elif old_level == 0:
                    current_list[name] = level
                    save_hunted() if is_hunted else save_friends()

        for name in list(online_cache):
            if name not in current_online_names:
                online_cache.remove(name)
                if name in hunted_players or name in friend_players:
                    await update_web_json(name, "---", "status", "Saiu do jogo", "off")
                    target_ch = ch_hunted if name in hunted_players else ch_friends
                    title = "🔴 ALVO OFFLINE" if name in hunted_players else "💤 AMIGO OFFLINE"
                    await target_ch.send(embed=discord.Embed(title=title, description=f"`{name}`", color=discord.Color.light_grey()))

@tasks.loop(seconds=65)
async def check_mortes():
    global last_deaths_ids
    data = await get_api_data("https://rubinot.com.br/deaths", 
                              "https://rubinot.com.br/api/deaths?world=21&page=1")
    
    if data and 'deaths' in data:
        for d in data['deaths']:
            player_name, raw_time = d.get('victim'), d.get('time')
            # ANTI-DUPE: Vítima + Tempo exato (Impossível repetir o mesmo segundo)
            death_id = f"{player_name}_{raw_time}" 

            if (player_name in hunted_players or player_name in friend_players) and death_id not in last_deaths_ids:
                last_deaths_ids.add(death_id)
                dt_object = datetime.fromtimestamp(int(raw_time))
                data_formatada = dt_object.strftime("%d/%m/%Y %H:%M:%S")
                
                is_player = d.get('is_player') == 1
                killer_raw = d.get('killed_by', 'Desconhecido')
                await update_web_json(player_name, d.get('level'), "pvp" if is_player else "pve", 
                                      f"Morto por {killer_raw.capitalize()}", "off", manual_datetime=data_formatada)
                
                target_channel = bot.get_channel(CHANNEL_ID if player_name in hunted_players else CHANNEL_FRIENDS)
                tipo_morte = "⚔️ MORTE EM PVP" if is_player else "👹 MORTE PARA MONSTRO"
                embed = discord.Embed(title=f"{tipo_morte}", color=discord.Color.red() if is_player else discord.Color.dark_grey(), timestamp=dt_object)
                embed.set_thumbnail(url="https://i.imgur.com/Gz7ta92.gif")
                embed.add_field(name="👤 Vítima", value=f"`{player_name}`", inline=True)
                embed.add_field(name="📊 Nível", value=f"{d.get('level')}", inline=True)
                embed.add_field(name="💀 Causa", value=f"**{killer_raw.capitalize()}**", inline=False)
                
                most_dmg = d.get('mostdamage_by')
                if most_dmg and most_dmg != killer_raw:
                    embed.add_field(name="🎯 Maior Dano", value=most_dmg.capitalize(), inline=True)
                
                embed.set_footer(text=f"Horário: {data_formatada}")
                await target_channel.send(embed=embed)

        if len(last_deaths_ids) > 300:
            last_deaths_ids = set(list(last_deaths_ids)[-150:])

@bot.command()
async def limpar(ctx, arg: str = "100"):
    if ctx.author.id not in AUTHORIZED_IDS: return
    def check(m): return m.author == bot.user or m.content.startswith("!")
    if arg.lower() == "tudo":
        await ctx.channel.purge(check=check)
        msg = await ctx.send("✅ Canal limpo completamente.")
    else:
        try:
            qtd = int(arg)
            deleted = await ctx.channel.purge(limit=qtd, check=check)
            msg = await ctx.send(f"✅ Removidas `{len(deleted)}` mensagens.")
        except: return
    await asyncio.sleep(5); await msg.delete()

@bot.command()
async def add(ctx, *, name: str):
    if name not in hunted_players:
        hunted_players[name] = 0; save_hunted(); await ctx.send(f"🎯 `{name}` adicionado.")

@bot.command()
async def remove(ctx, *, name: str):
    if name in hunted_players:
        del hunted_players[name]; save_hunted(); await ctx.send(f"🕊️ `{name}` removido.")

@bot.command()
async def friend(ctx, *, name: str):
    if name not in friend_players:
        friend_players[name] = 0; save_friends(); await ctx.send(f"💎 `{name}` adicionado.")

@bot.command()
async def unfriend(ctx, *, name: str):
    if name in friend_players:
        del friend_players[name]; save_friends(); await ctx.send(f"👋 `{name}` removido.")

@bot.command()
async def masspush(ctx):
    if ctx.author.id not in AUTHORIZED_IDS or not ctx.author.voice: return
    dest = ctx.author.voice.channel
    count = 0
    for channel in ctx.guild.voice_channels:
        if channel == dest: continue
        for member in channel.members:
            try: await member.move_to(dest); count += 1; await asyncio.sleep(0.1)
            except: pass
    await ctx.send(f"✅ `{count}` membros movidos.")

@bot.command()
async def masspoke(ctx, *, mensagem: str):
    if ctx.author.id not in AUTHORIZED_IDS: return
    await ctx.send(f"📢 Mass Poke: `{mensagem}`")
    try:
        if os.path.exists("mass_poke.mp3"): os.remove("mass_poke.mp3")
        gTTS(text=mensagem, lang='pt', tld='com.br').save("mass_poke.mp3")
        for channel in ctx.guild.voice_channels:
            if not channel.members: continue
            try:
                vc = await channel.connect()
                vc.play(discord.FFmpegPCMAudio("mass_poke.mp3"))
                while vc.is_playing(): await asyncio.sleep(0.5)
                await vc.disconnect(); await asyncio.sleep(0.5) 
            except:
                if ctx.voice_client: await ctx.voice_client.disconnect()
        await ctx.send("✅ Finalizado!")
    except Exception as e: await ctx.send(f"❌ Erro: {e}")

@bot.event
async def on_ready():
    global hunted_players, friend_players, web_events
    print(f"✅ Bot Online: {bot.user}")
    if os.path.exists(FILE):
        with open(FILE, "r") as f: hunted_players = json.load(f)
    if os.path.exists(FILE_FRIENDS):
        with open(FILE_FRIENDS, "r") as f: friend_players = json.load(f)
    if os.path.exists(WEB_JSON):
        try:
            with open(WEB_JSON, "r", encoding="utf-8") as f: web_events = json.load(f)
        except: web_events = []
    if not radar_principal.is_running(): radar_principal.start()
    if not check_mortes.is_running(): check_mortes.start()

bot.run(TOKEN)
