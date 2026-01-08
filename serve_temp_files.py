"""
Script para servir archivos temporales de OnlyOffice.
Ejecuta este script en una terminal separada para hacer los archivos accesibles.
"""

import http.server
import socketserver
import os
import sys

# Directorio de archivos temporales
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_onlyoffice")
PORT = 8000

# Crear directorio si no existe
os.makedirs(TEMP_DIR, exist_ok=True)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=TEMP_DIR, **kwargs)
    
    def end_headers(self):
        # Agregar headers CORS para permitir que OnlyOffice acceda
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

def main():
    print(f"📁 Sirviendo archivos desde: {TEMP_DIR}")
    print(f"🌐 Servidor iniciado en: http://localhost:{PORT}")
    print(f"🌐 Acceso en red: http://172.17.87.11:{PORT}")
    print("\n💡 Para usar en OnlyOffice, usa la URL:")
    print(f"   http://172.17.87.11:{PORT}/nombre-archivo.xlsx")
    print("\n⚠️ Presiona Ctrl+C para detener el servidor\n")
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Servidor detenido")
        sys.exit(0)

if __name__ == "__main__":
    main()
