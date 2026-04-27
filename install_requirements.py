import subprocess
import sys

def install():
    print("🚀 Instalando dependências...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    print("🌐 Configurando navegadores do Playwright...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    
    print("✅ Instalação concluída.")

if __name__ == "__main__":
    install()