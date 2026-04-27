import subprocess
import time
import sys
import os
from pyngrok import ngrok

# --- CONFIGURAÇÕES ---
PORT = 8000
BOT_SCRIPT = "bot_hunted.py"
NGROK_TOKEN = "3Cuq7p1hWuzEIleFQwEtEjPjWOG_5jat1gC6nwQLy7QdqGxiv"

def start_system():
    processes = []

    try:
        print("🔥 --- BIKINI BOTTOM RADAR SYSTEM --- 🔥")

        # 1. Configurar Authtoken do Ngrok
        print("🔑 Autenticando Ngrok...")
        ngrok.set_auth_token(NGROK_TOKEN)

        # 2. Iniciar Servidor Web na porta 8000
        print(f"📡 Iniciando Servidor Web na porta {PORT}...")
        web_server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(web_server)

        # 3. Iniciar Túnel Ngrok
        print("🔗 Criando túnel externo...")
        public_url = ngrok.connect(PORT, "http")
        
        print("\n" + "="*40)
        print(f"🌍 PAINEL ONLINE: {public_url.public_url}")
        print(f"🏠 LOCALHOST: http://localhost:{PORT}")
        print("="*40 + "\n")

        # 4. Iniciar o Bot
        print(f"🤖 Iniciando {BOT_SCRIPT}...\n")
        # subprocess.run mantém o processo "preso" aqui para você ver os logs do bot
        subprocess.run([sys.executable, BOT_SCRIPT])

    except KeyboardInterrupt:
        print("\n\n🛑 Encerrando sistema...")
    except Exception as e:
        print(f"❌ Erro Crítico: {e}")
    finally:
        print("🧹 Limpando processos e fechando túneis...")
        for p in processes:
            p.terminate()
        ngrok.kill()
        print("✅ Sistema desligado.")

if __name__ == "__main__":
    start_system()