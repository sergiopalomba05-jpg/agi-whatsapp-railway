"""
Keep-Alive automático para Render
Mantiene el servicio de Render activo enviando pings periódicos
"""
import requests
import time
from datetime import datetime

class KeepAliveRender:
    def __init__(self, render_url):
        self.render_url = render_url
        self.intervalo_segundos = 300  # 5 minutos
        
    def ping(self):
        """Envía un ping al servicio de Render."""
        try:
            response = requests.get(self.render_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Ping exitoso")
                return True
            else:
                print(f"⚠️  Error {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def iniciar(self):
        """Inicia el ciclo de keep-alive."""
        print(f"🚀 Iniciando Keep-Alive para {self.render_url}")
        print("=" * 70)
        
        while True:
            self.ping()
            time.sleep(self.intervalo_segundos)

def main():
    render_url = "https://agi-telegram2-0.onrender.com"
    keep_alive = KeepAliveRender(render_url)
    keep_alive.iniciar()

if __name__ == "__main__":
    main()
