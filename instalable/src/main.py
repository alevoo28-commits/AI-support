"""
Sistema de Configuración Automática de Red - FCFM UCHILE
Versión: 1.0
Autor: Sistema de Gestión de Red
"""

import os

# Utilidad para leer el client_id (email) enviado desde la web
def obtener_client_id():
    client_id_path = os.path.join(os.path.dirname(__file__), "client_id.txt")
    if os.path.exists(client_id_path):
        try:
            with open(client_id_path, "r", encoding="utf-8") as f:
                client_id = f.read().strip()
                if client_id:
                    return client_id
        except Exception:
            pass
    return os.getenv('USUARIO', 'desconocido')
import sys
import time
import logging
from datetime import datetime
from network_manager import NetworkManager
from database_manager import DatabaseManager
from ip_finder import IPFinder
from dotenv import load_dotenv
import requests

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

# Segmentos de red permitidos
ALLOWED_SEGMENTS = [
    '172.17.82',
    '172.17.83',
    '172.17.84',
    '172.17.85',
    '172.17.86',
    '172.17.87'
]

def enviar_resultado_al_servidor(data, url="http://172.17.87.11:5000/api/report"):
    """Envía los resultados de conectividad al servidor IA support por HTTP POST"""
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            logging.info(f"Reporte enviado correctamente: {response.json()}")
            return True
        else:
            logging.error(f"Error al enviar reporte: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"Excepción al enviar reporte: {e}")
        return False

def print_banner():
    """Muestra el banner del sistema"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║   Sistema de Configuración Automática de Red              ║
    ║   FCFM - Universidad de Chile                             ║
    ║   Versión 1.0                                             ║
    ╚═══════════════════════════════════════════════════════════╝
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
    """Función principal del sistema"""
    print_banner()
    verificar_permisos_admin()
    
    # Cargar variables de entorno
    load_dotenv()
    
    try:
        # Inicializar componentes
        print("\n[1/6] Inicializando sistema...")
        logger.info("Inicializando componentes del sistema")
        
        network_mgr = NetworkManager()
        db_mgr = DatabaseManager()
        ip_finder = IPFinder()
        
        # Paso 1: Verificar conectividad a Internet
        print("\n[2/6] Verificando conectividad a Internet...")
        logger.info("Verificando conectividad a Internet")
        
        tiene_internet = network_mgr.verificar_internet()
        if tiene_internet:
            print("✓ Conexión a Internet OK")
            logger.info("Conexión a Internet establecida correctamente")
            print("\nNo se requieren cambios en la configuración de red.")
            # Enviar resultado exitoso al servidor IA support
            datos_reporte = {
                "usuario": obtener_client_id(),
                "resultado": "Conexión a Internet OK",
                "timestamp": datetime.now().isoformat()
            }
            enviar_resultado_al_servidor(datos_reporte)
            input("\nPresiona Enter para salir...")
            return
        print("✗ Sin conexión a Internet")
        logger.warning("No hay conexión a Internet, iniciando diagnóstico")
        
        # Paso 2: Obtener configuración actual
        print("\n[3/6] Obteniendo configuración de red actual...")
        logger.info("Obteniendo configuración de red")
        
        config_actual = network_mgr.obtener_configuracion_ethernet()
        
        if not config_actual or not config_actual.get('ip'):
            print("✗ No se pudo obtener la IP actual o no hay IP asignada")
            logger.error("No se detectó IP en el adaptador Ethernet")

            # Solicitar datos personales al usuario
            print("\nPor favor, ingrese sus datos para registrar un nuevo usuario en la red:")
            nombre = input("Nombre: ").strip()
            apellido = input("Apellido: ").strip()
            correo = input("Correo (@uchile.cl): ").strip()
            contacto = input("Contacto o anexo: ").strip()
            departamento = input("Departamento: ").strip()

            # Insertar datos en la base de datos
            if db_mgr.conectar():
                try:
                    cursor = db_mgr.conexion.cursor()
                    query = "INSERT INTO personal (nombre, apellido, correo, contacto, departamento) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(query, (nombre, apellido, correo, contacto, departamento))
                    db_mgr.conexion.commit()
                    cursor.close()
                    print("✓ Usuario registrado en la base de datos.")
                    logger.info(f"Usuario {nombre} {apellido} registrado en BD.")
                except Exception as e:
                    print(f"✗ Error al registrar usuario: {e}")
                    logger.error(f"Error al registrar usuario: {e}")
                db_mgr.desconectar()
            else:
                print("✗ No se pudo conectar a la base de datos para registrar usuario.")
                logger.error("No se pudo conectar a la base de datos para registrar usuario.")

            # Ejecutar IA support y enviar resultados de pruebas de conectividad
            print("\nEjecutando agente IA support para pruebas locales...")
            try:
                import subprocess
                resultado_ping = os.system("ping -n 1 8.8.8.8")
                resultado = subprocess.run([
                    sys.executable,
                    "..\\IA-support\\main.py" # Ajusta el nombre si el entrypoint es diferente
                ], input=f"No tengo conexion a internet. Resultado ping: {resultado_ping}", text=True, capture_output=True)
                print("Respuesta IA support:")
                print(resultado.stdout)
                logger.info(f"Respuesta IA support: {resultado.stdout}")
                # Enviar resultado al servidor IA support
                datos_reporte = {
                    "usuario": obtener_client_id(),
                    "correo": correo,
                    "departamento": departamento,
                    "resultado": "Sin conexión a internet",
                    "ping": resultado_ping,
                    "respuesta_ia": resultado.stdout,
                    "timestamp": datetime.now().isoformat()
                }
                enviar_resultado_al_servidor(datos_reporte)
            except Exception as e:
                print(f"✗ Error ejecutando IA support: {e}")
                logger.error(f"Error ejecutando IA support: {e}")
        else:
            ip_actual = config_actual['ip']
            print(f"✓ IP actual: {ip_actual}")
            logger.info(f"IP actual detectada: {ip_actual}")
            
            # Paso 3: Conectar a base de datos y obtener IPs usadas
            print("\n[4/6] Conectando a base de datos...")
            logger.info("Conectando a MySQL")
            
            if not db_mgr.conectar():
                print("✗ Error al conectar a la base de datos")
                logger.error("Fallo en conexión a base de datos")
                input("\nPresiona Enter para salir...")
                return
            
            print("✓ Conexión a base de datos establecida")
            
            ips_usadas = db_mgr.obtener_ips_usadas()
            print(f"✓ IPs registradas en base de datos: {len(ips_usadas)}")
            logger.info(f"Se obtuvieron {len(ips_usadas)} IPs de la base de datos")
            
            # Paso 4: Buscar IP disponible
            print("\n[5/6] Buscando IP disponible...")
            logger.info("Iniciando búsqueda de IP disponible")
            
            # Determinar el segmento de red de la base de datos
            segmento_bd = os.getenv('NETWORK_SEGMENT', '172.17.82')
            
            # Verificar si la IP actual está en el mismo segmento
            segmento_actual = '.'.join(ip_actual.split('.')[:3])
            
            if segmento_actual in ALLOWED_SEGMENTS:
                print(f"✓ Segmento actual ({segmento_actual}.x) es válido")
                logger.info(f"Segmento actual válido: {segmento_actual}")
                
                # Buscar IP disponible en el mismo segmento
                ip_disponible = ip_finder.buscar_ip_disponible_segmento(
                    segmento_actual, 
                    ips_usadas
                )
            else:
                print(f"✗ Segmento actual ({segmento_actual}.x) no es válido")
                logger.warning(f"Segmento inválido: {segmento_actual}, usando segmento BD")
                
                # Realizar ping sweep en el segmento de la BD
                ip_disponible = ip_finder.buscar_ip_con_ping_sweep(
                    segmento_bd,
                    ips_usadas
                )
            
            if not ip_disponible:
                print("✗ No se encontró una IP disponible")
                logger.error("No se pudo encontrar una IP disponible")
                input("\nPresiona Enter para salir...")
                return
            
            print(f"✓ IP disponible encontrada: {ip_disponible}")
            logger.info(f"IP disponible seleccionada: {ip_disponible}")
            
            # Paso 5: Configurar la nueva IP
            print("\n[6/6] Configurando nueva IP en adaptador Ethernet...")
            logger.info(f"Configurando IP {ip_disponible}")
            
            mascara = os.getenv('SUBNET_MASK', '255.255.255.0')
            gateway = os.getenv('GATEWAY', f"{'.'.join(ip_disponible.split('.')[:3])}.1")
            dns_primary = os.getenv('DNS_PRIMARY', '172.17.66.9')
            dns_secondary = os.getenv('DNS_SECONDARY', '172.17.40.9')
            
            exito = network_mgr.configurar_ip_estatica(
                ip_disponible,
                mascara,
                gateway,
                dns_primary,
                dns_secondary
            )
            
            if exito:
                print(f"\n✓ Configuración aplicada exitosamente")
                print(f"  - IP: {ip_disponible}")
                print(f"  - Máscara: {mascara}")
                print(f"  - Gateway: {gateway}")
                print(f"  - DNS: {dns_primary}, {dns_secondary}")
                logger.info("Configuración de red aplicada correctamente")
                
                # Registrar en base de datos
                if db_mgr.registrar_ip(ip_disponible):
                    print(f"✓ IP registrada en base de datos")
                    logger.info(f"IP {ip_disponible} registrada en BD")
                
                # Verificar conectividad nuevamente
                print("\nVerificando conectividad...")
                time.sleep(3)
                
                if network_mgr.verificar_internet():
                    print("✓ ¡Conexión a Internet establecida!")
                    logger.info("Conexión a Internet restaurada exitosamente")
                    # Enviar resultado exitoso al servidor IA support
                    datos_reporte = {
                        "ip": ip_disponible,
                        "usuario": obtener_client_id(),
                        "resultado": "Conexión a Internet establecida",
                        "timestamp": datetime.now().isoformat()
                    }
                    enviar_resultado_al_servidor(datos_reporte)
                else:
                    print("✗ Aún no hay conexión a Internet. Verifica el gateway y DNS.")
                    logger.warning("No se estableció conexión a Internet después de la configuración")
                    # Enviar resultado fallido al servidor IA support
                    datos_reporte = {
                        "ip": ip_disponible,
                        "usuario": obtener_client_id(),
                        "resultado": "No se estableció conexión a Internet después de la configuración",
                        "timestamp": datetime.now().isoformat()
                    }
                    enviar_resultado_al_servidor(datos_reporte)
            else:
                print("\n✗ Error al aplicar la configuración")
                logger.error("Fallo al aplicar configuración de red")
        
        db_mgr.desconectar()
        
    except Exception as e:
        logger.error(f"Error en el proceso principal: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
    
    print(f"\nLog guardado en: {log_file}")
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()
