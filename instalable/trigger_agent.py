import time
import requests
import subprocess
import os
import sys
from datetime import datetime


# Permitir que el CLIENT_ID (email) se lea de un archivo generado por la web
SERVER_URL = "http://172.17.87.11:5000"
CLIENT_ID_FILE = os.path.join(os.path.dirname(__file__), 'client_id.txt')
def get_client_id():
    # Prioridad: archivo client_id.txt > env > fallback
    if os.path.exists(CLIENT_ID_FILE):
        with open(CLIENT_ID_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return os.getenv('COMPUTERNAME', 'cliente_windows')

MAIN_EXE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dist', 'main.exe'))
MAIN_PY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))

POLL_INTERVAL = 10  # segundos

def ejecutar_diagnostico():
    print(f"[{datetime.now()}] Ejecutando diagnóstico de conectividad...")
    if os.path.exists(MAIN_EXE_PATH):
        subprocess.run([MAIN_EXE_PATH], check=False)
    elif os.path.exists(MAIN_PY_PATH):
        subprocess.run([sys.executable, MAIN_PY_PATH], check=False)
    else:
        print("No se encontró main.exe ni main.py para ejecutar el diagnóstico.")

def limpiar_trigger():
    try:
        requests.post(f"{SERVER_URL}/api/trigger-test/clear")
    except Exception:
        pass


def main():
    client_id = get_client_id()
    print(f"Agente de escucha de triggers iniciado para {client_id}")
    while True:
        try:
            resp = requests.get(f"{SERVER_URL}/api/trigger-test")
            data = resp.json()
            if data.get('trigger') and data.get('client_id') == client_id:
                print(f"[{datetime.now()}] Trigger recibido. Ejecutando diagnóstico...")
                ejecutar_diagnostico()
                limpiar_trigger()
            else:
                print(f"[{datetime.now()}] Sin trigger pendiente.")
        except Exception as e:
            print(f"[{datetime.now()}] Error consultando trigger: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
