import threading
from flask import Flask
import discord
from discord.ext import commands

app = Flask(__name__)

@app.route("/")
def home():
    return "OK Bot online"

def run_flask():
    app.run(host="0.0.0.0", port=5000)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")

def run_bot():
    bot.run("SEU_TOKEN_AQUI")  # ou os.getenv("TOKEN")


# 🔥 ISSO AQUI É O QUE FALTA
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
