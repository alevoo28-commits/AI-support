"""
Buscador de IPs - Encuentra IPs disponibles en la red
"""

import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class IPFinder:
    def __init__(self):
        self.segmentos_validos = [
            '172.17.82',
            '172.17.83',
            '172.17.84',
            '172.17.85',
            '172.17.86',
            '172.17.87'
        ]
    
    def buscar_ip_disponible_segmento(self, segmento, ips_usadas, rango_inicio=10, rango_fin=254):
        """
        Busca una IP disponible en el segmento especificado
        que no esté en la lista de IPs usadas
        """
        logger.info(f"Buscando IP disponible en segmento {segmento}.x")
        
        for i in range(rango_inicio, rango_fin + 1):
            ip_candidata = f"{segmento}.{i}"
            
            if ip_candidata not in ips_usadas:
                logger.info(f"IP candidata encontrada: {ip_candidata}")
                return ip_candidata
        
        logger.warning(f"No se encontró IP disponible en segmento {segmento}.x")
        return None
    
    def _hacer_ping(self, ip):
        """Hace ping a una IP específica y retorna True si NO responde (disponible)"""
        try:
            resultado = subprocess.run(
                ['ping', '-n', '1', '-w', '500', ip],
                capture_output=True,
                timeout=2
            )
            # Retorna True si NO hay respuesta (IP disponible)
            return resultado.returncode != 0
        except Exception:
            return True
    
    def buscar_ip_con_ping_sweep(self, segmento, ips_usadas, rango_inicio=10, rango_fin=254):
        """
        Realiza un ping sweep al segmento para encontrar IPs que no respondan
        y que no estén en la base de datos
        """
        logger.info(f"Iniciando ping sweep en segmento {segmento}.x")
        print(f"  Escaneando rango {segmento}.{rango_inicio}-{rango_fin}...")
        
        ips_candidatas = []
        
        # Crear lista de IPs a verificar
        ips_a_verificar = [
            f"{segmento}.{i}" 
            for i in range(rango_inicio, rango_fin + 1)
        ]
        
        # Usar ThreadPoolExecutor para hacer pings en paralelo
        with ThreadPoolExecutor(max_workers=50) as executor:
            # Enviar todas las tareas
            futuro_a_ip = {
                executor.submit(self._hacer_ping, ip): ip 
                for ip in ips_a_verificar
            }
            
            # Procesar resultados
            completados = 0
            total = len(futuro_a_ip)
            
            for futuro in as_completed(futuro_a_ip):
                ip = futuro_a_ip[futuro]
                completados += 1
                
                if completados % 20 == 0:
                    print(f"  Progreso: {completados}/{total}")
                
                try:
                    no_responde = futuro.result()
                    
                    # Si no responde y no está en BD, es candidata
                    if no_responde and ip not in ips_usadas:
                        ips_candidatas.append(ip)
                        logger.info(f"IP disponible encontrada: {ip}")
                        
                except Exception as e:
                    logger.warning(f"Error verificando {ip}: {e}")
        
        if ips_candidatas:
            # Retornar la primera IP disponible
            ip_seleccionada = ips_candidatas[0]
            logger.info(f"IP seleccionada del ping sweep: {ip_seleccionada}")
            print(f"  ✓ Se encontraron {len(ips_candidatas)} IPs disponibles")
            return ip_seleccionada
        
        logger.warning(f"No se encontraron IPs disponibles en ping sweep de {segmento}.x")
        return None
