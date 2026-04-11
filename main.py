import threading
import os
import json
from flask import Flask, jsonify, render_template_string
import discord
from discord.ext import commands

# ---------------- FILE ----------------
FILE = "players.json"

def load_players():
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return []

# ---------------- FLASK ----------------
app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Tracker Dashboard</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { background:#0f0f0f; color:white; font-family:Arial; }
        .box { padding:20px; }
        .player { padding:6px; border-bottom:1px solid #333; }
    </style>
</head>
<body>
    <div class="box">
        <h1>🔥 Tracker Dashboard</h1>
        <h3>Players monitorados:</h3>
        {% for p in players %}
            <div class="player">{{p}}</div>
        {% endfor %}
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    players = load_players()
    return render_template_string(HTML, players=players)

@app.route("/api")
def api():
    return jsonify(load_players())

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# ---------------- DISCORD BOT ----------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

tracked_players = set()

@bot.event
async def on_ready():
    print(f"🔥 Bot online: {bot.user}")

@bot.command()
async def track(ctx, *, name):
    tracked_players.add(name)

    with open(FILE, "w") as f:
        json.dump(list(tracked_players), f)

    await ctx.send(f"✅ {name} adicionado")

@bot.command(name="list")
async def list_cmd(ctx):
    await ctx.send("\n".join(tracked_players) if tracked_players else "vazio")

def run_bot():
    bot.run(os.getenv("TOKEN"))

# ---------------- START ----------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
