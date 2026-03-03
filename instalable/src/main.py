"""
Configurador de Red - FCFM Universidad de Chile
Ejecuta como Administrador.

Flujo:
  1. Verifica si ya hay conectividad â†’ si la hay, sale.
  2. Pide el correo del usuario (para registrar en MySQL).
  3. Consulta MySQL: obtiene IPs ya asignadas.
  4. Genera pool de IPs candidatas en los segmentos 172.17.82-87.x
  5. Por cada candidata (sin ping response):
       - Aplica IP en el adaptador Ethernet.
       - Espera y prueba conectividad (ping 8.8.8.8).
       - Si hay conectividad â†’ actualiza IP en MySQL â†’ termina.
  6. Muestra resultado en consola y en log.
"""

import os
import sys
import time
import logging
import subprocess
import ctypes
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from network_manager import NetworkManager
from database_manager import DatabaseManager
from dotenv import load_dotenv

# Configurar logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"network_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

ALLOWED_SEGMENTS = [
    '172.17.82', '172.17.83', '172.17.84',
    '172.17.85', '172.17.86', '172.17.87',
]

def _ping_responde(ip: str) -> bool:
    """Retorna True si la IP responde a ping (estÃ¡ ocupada)."""
    try:
        r = subprocess.run(
            ['ping', '-n', '1', '-w', '500', ip],
            capture_output=True, timeout=3
        )
        return r.returncode == 0
    except Exception:
        return False


def generar_pool_candidatas(ips_usadas: set, max_por_segmento: int = 254) -> list:
    """Genera IPs candidatas en paralelo descartando usadas y las que respondan ping."""
    candidatas = []
    for seg in ALLOWED_SEGMENTS:
        for i in range(2, max_por_segmento + 1):
            ip = f"{seg}.{i}"
            if ip not in ips_usadas:
                candidatas.append(ip)

    # Filtrar las que responden ping en paralelo
    logger.info(f"Verificando {len(candidatas)} IPs candidatas con ping sweep...")
    print(f"  Verificando {len(candidatas)} IPs (esto puede tomar unos segundos)...")

    libres = []
    with ThreadPoolExecutor(max_workers=100) as ex:
        fut_map = {ex.submit(_ping_responde, ip): ip for ip in candidatas}
        for fut in as_completed(fut_map):
            ip = fut_map[fut]
            try:
                if not fut.result():
                    libres.append(ip)
            except Exception:
                libres.append(ip)  # Si falla el ping, asumir libre

    # Ordenar para iterar de menor a mayor
    libres.sort(key=lambda x: tuple(int(p) for p in x.split('.')))
    logger.info(f"IPs libres encontradas: {len(libres)}")
    return libres

def print_banner():
    """Muestra el banner del sistema"""
    banner = """
    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
    â•‘   Sistema de ConfiguraciÃ³n AutomÃ¡tica de Red              â•‘
    â•‘   FCFM - Universidad de Chile                             â•‘
    â•‘   VersiÃ³n 1.0                                             â•‘
    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    """
    print(banner)
    logger.info("Sistema iniciado")

def verificar_permisos_admin():
    """Verifica si el script se ejecuta con permisos de administrador"""
    try:
        import ctypes
        es_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not es_admin:
            logger.error("El programa necesita permisos de administrador")
            print("\n[ERROR] Este programa necesita ejecutarse como Administrador")
            print("Por favor, haz clic derecho sobre el ejecutable y selecciona 'Ejecutar como administrador'")
            input("\nPresiona Enter para salir...")
            sys.exit(1)
        logger.info("Permisos de administrador verificados")
    except Exception as e:
        logger.error(f"Error verificando permisos: {e}")
        sys.exit(1)

def main():
    """FunciÃ³n principal."""
    print_banner()
    verificar_permisos_admin()
    load_dotenv()

    try:
        network_mgr = NetworkManager()
        db_mgr = DatabaseManager()

        # PASO 1: Verificar si ya hay conectividad
        print("\n[1/5] Verificando conectividad actual...")
        if network_mgr.verificar_internet():
            print("âœ“ Ya tienes conexiÃ³n a Internet. No se requieren cambios.")
            logger.info("Conectividad OK, sin cambios necesarios.")
            input("\nPresiona Enter para salir...")
            return

        # PASO 2: Pedir correo del usuario
        print("\n[2/5] IdentificaciÃ³n del usuario")
        correo = input("  Ingresa tu correo institucional (@uchile.cl): ").strip()
        if not correo:
            print("âœ— Correo requerido para registrar la IP.")
            input("\nPresiona Enter para salir...")
            return

        # PASO 3: Conectar a MySQL y obtener IPs ya asignadas
        print("\n[3/5] Conectando a base de datos...")
        if not db_mgr.conectar():
            print("âœ— No se pudo conectar a la base de datos.")
            print("  Verifica la conexiÃ³n de red y las credenciales en el archivo .env")
            logger.error("Fallo conexiÃ³n MySQL")
            input("\nPresiona Enter para salir...")
            return

        print("âœ“ ConexiÃ³n a base de datos establecida")
        ips_usadas = set(db_mgr.obtener_ips_usadas())
        print(f"  IPs ya asignadas en BD: {len(ips_usadas)}")
        logger.info(f"IPs usadas en MySQL: {len(ips_usadas)}")

        # PASO 4: Generar pool de candidatas (sin ping response, sin asignadas en BD)
        print("\n[4/5] Buscando IPs disponibles en los segmentos de red...")
        candidatas = generar_pool_candidatas(ips_usadas)

        if not candidatas:
            print("âœ— No hay IPs disponibles en el pool.")
            logger.error("Pool de IPs vacÃ­o.")
            db_mgr.desconectar()
            input("\nPresiona Enter para salir...")
            return

        print(f"  {len(candidatas)} IPs candidatas disponibles.")

        # PASO 5: Iterar IPs hasta encontrar una con conectividad
        print("\n[5/5] Asignando IP y verificando conectividad...")
        mascara  = os.getenv('SUBNET_MASK', '255.255.255.0')
        dns_pri  = os.getenv('DNS_PRIMARY', '172.17.66.9')
        dns_sec  = os.getenv('DNS_SECONDARY', '172.17.40.9')
        MAX_INTENTOS = 15
        ip_exitosa = None
        gateway    = os.getenv('GATEWAY', '')

        for intento, ip in enumerate(candidatas[:MAX_INTENTOS], start=1):
            gw = gateway if gateway else '.'.join(ip.split('.')[:3]) + '.1'
            print(f"  Intento {intento}/{MAX_INTENTOS}: aplicando {ip}  (gw {gw})...")
            logger.info(f"Intentando IP {ip}")

            ok = network_mgr.configurar_ip_estatica(ip, mascara, gw, dns_pri, dns_sec)
            if not ok:
                print(f"  âœ— No se pudo aplicar {ip}, probando siguiente...")
                logger.warning(f"FallÃ³ aplicar IP {ip}")
                continue

            time.sleep(3)  # Esperar a que el adaptador aplique la config

            if network_mgr.verificar_internet():
                print(f"  âœ“ Â¡Conectividad OK con IP {ip}!")
                logger.info(f"Conectividad OK con IP {ip}")
                ip_exitosa = ip
                final_gw = gw
                break
            else:
                print(f"  âœ— {ip} sin conectividad, probando siguiente...")
                logger.warning(f"IP {ip} sin conectividad")

        if not ip_exitosa:
            print(f"\nâœ— No se obtuvo conectividad tras {min(len(candidatas), MAX_INTENTOS)} intentos.")
            print("  Verifica el cable de red, el switch y el gateway.")
            logger.error("Sin conectividad tras agotar intentos.")
            db_mgr.desconectar()
            input("\nPresiona Enter para salir...")
            return

        # Registrar IP en MySQL asociada al correo del usuario
        print(f"\nâœ“ Registrando IP {ip_exitosa} para {correo} en la base de datos...")
        if db_mgr.registrar_o_actualizar_ip(correo, ip_exitosa):
            print("âœ“ IP registrada correctamente.")
            logger.info(f"IP {ip_exitosa} registrada para {correo} en MySQL.")
        else:
            print("âš  IP aplicada pero no se pudo registrar en la base de datos.")
            logger.warning("No se registrÃ³ IP en MySQL.")

        print(f"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘  âœ…  CONFIGURACIÃ“N COMPLETADA                   â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘  IP asignada : {ip_exitosa:<33}â•‘
â•‘  MÃ¡scara     : {mascara:<33}â•‘
â•‘  Gateway     : {final_gw:<33}â•‘
â•‘  DNS         : {dns_pri + ", " + dns_sec:<33}â•‘
â•‘  Usuario     : {correo:<33}â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        """)
        logger.info("Proceso completado exitosamente.")
        db_mgr.desconectar()

    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")

    print(f"\nLog guardado en: {log_file}")
    input("\nPresiona Enter para salir...")


if __name__ == "__main__":
    main()

