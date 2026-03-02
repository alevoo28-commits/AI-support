"""
Gestor de Red - Manejo de configuración de adaptadores de red
"""

import subprocess
import socket
import logging

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self):
        self.adaptador_ethernet = self._obtener_nombre_adaptador()
    
    def _obtener_nombre_adaptador(self):
        """Obtiene el nombre del adaptador Ethernet principal"""
        try:
            # Ejecutar ipconfig para encontrar el adaptador Ethernet
            resultado = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                encoding='cp850'
            )
            
            lineas = resultado.stdout.split('\n')
            for i, linea in enumerate(lineas):
                if 'Ethernet' in linea and 'adaptador' in linea.lower():
                    # Extraer el nombre del adaptador
                    nombre = linea.split(':')[0].strip()
                    logger.info(f"Adaptador Ethernet encontrado: {nombre}")
                    return nombre
            
            # Nombre por defecto
            logger.warning("No se encontró adaptador Ethernet, usando nombre por defecto")
            return "Ethernet"
        except Exception as e:
            logger.error(f"Error obteniendo nombre de adaptador: {e}")
            return "Ethernet"
    
    def verificar_internet(self, hosts=['8.8.8.8', '1.1.1.1']):
        """Verifica conectividad a Internet haciendo ping a servidores DNS públicos"""
        for host in hosts:
            try:
                # Ping usando subprocess
                resultado = subprocess.run(
                    ['ping', '-n', '1', '-w', '1000', host],
                    capture_output=True
                )
                if resultado.returncode == 0:
                    logger.info(f"Ping exitoso a {host}")
                    return True
            except Exception as e:
                logger.warning(f"Error haciendo ping a {host}: {e}")
                continue
        
        logger.warning("No hay conectividad a Internet")
        return False
    
    def obtener_configuracion_ethernet(self):
        """Obtiene la configuración actual del adaptador Ethernet"""
        try:
            resultado = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                encoding='cp850'
            )
            
            lineas = resultado.stdout.split('\n')
            config = {}
            en_ethernet = False
            
            for linea in lineas:
                if self.adaptador_ethernet in linea:
                    en_ethernet = True
                    continue
                
                if en_ethernet:
                    if 'adaptador' in linea.lower():
                        break
                    
                    if 'IPv4' in linea or 'Dirección IPv4' in linea:
                        partes = linea.split(':')
                        if len(partes) > 1:
                            ip = partes[1].strip().split('(')[0].strip()
                            config['ip'] = ip
                    
                    if 'Máscara de subred' in linea or 'Subnet Mask' in linea:
                        partes = linea.split(':')
                        if len(partes) > 1:
                            config['mascara'] = partes[1].strip()
                    
                    if 'Puerta de enlace' in linea or 'Default Gateway' in linea:
                        partes = linea.split(':')
                        if len(partes) > 1:
                            gateway = partes[1].strip()
                            if gateway:
                                config['gateway'] = gateway
            
            logger.info(f"Configuración actual: {config}")
            return config
        
        except Exception as e:
            logger.error(f"Error obteniendo configuración: {e}")
            return {}
    
    def configurar_ip_estatica(self, ip, mascara, gateway, dns1, dns2):
        """Configura una IP estática en el adaptador Ethernet"""
        try:
            # Configurar IP y máscara
            cmd_ip = [
                'netsh', 'interface', 'ip', 'set', 'address',
                f'name={self.adaptador_ethernet}',
                'static', ip, mascara, gateway
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd_ip)}")
            resultado = subprocess.run(cmd_ip, capture_output=True, text=True)
            
            if resultado.returncode != 0:
                logger.error(f"Error configurando IP: {resultado.stderr}")
                return False
            
            # Configurar DNS primario
            cmd_dns1 = [
                'netsh', 'interface', 'ip', 'set', 'dns',
                f'name={self.adaptador_ethernet}',
                'static', dns1
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd_dns1)}")
            subprocess.run(cmd_dns1, capture_output=True)
            
            # Configurar DNS secundario
            cmd_dns2 = [
                'netsh', 'interface', 'ip', 'add', 'dns',
                f'name={self.adaptador_ethernet}',
                dns2, 'index=2'
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd_dns2)}")
            subprocess.run(cmd_dns2, capture_output=True)
            
            logger.info("Configuración de red aplicada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error configurando IP estática: {e}")
            return False
