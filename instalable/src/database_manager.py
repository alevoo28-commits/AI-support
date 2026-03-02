"""
Gestor de Base de Datos - Conexión y consultas a MySQL
"""

import os
import logging
import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conexion = None
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 3306))
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'FCFMUCHILE')
    
    def conectar(self):
        """Establece conexión con la base de datos MySQL"""
        try:
            self.conexion = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            
            if self.conexion.is_connected():
                logger.info(f"Conexión exitosa a {self.database}")
                return True
            
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            return False
    
    def obtener_ips_usadas(self):
        """Obtiene todas las IPs registradas en la tabla personal"""
        ips = []
        try:
            cursor = self.conexion.cursor()
            query = "SELECT IP FROM personal WHERE IP IS NOT NULL AND IP != ''"
            cursor.execute(query)
            
            resultados = cursor.fetchall()
            ips = [fila[0] for fila in resultados if fila[0]]
            
            cursor.close()
            logger.info(f"IPs obtenidas de BD: {len(ips)}")
            
        except Error as e:
            logger.error(f"Error obteniendo IPs: {e}")
        
        return ips
    
    def registrar_ip(self, ip):
        """Registra una nueva IP en la tabla personal"""
        try:
            cursor = self.conexion.cursor()
            
            # Verificar si la IP ya existe
            query_check = "SELECT COUNT(*) FROM personal WHERE IP = %s"
            cursor.execute(query_check, (ip,))
            
            if cursor.fetchone()[0] > 0:
                logger.warning(f"La IP {ip} ya existe en la base de datos")
                cursor.close()
                return False
            
            # Insertar nueva IP
            query_insert = "INSERT INTO personal (IP) VALUES (%s)"
            cursor.execute(query_insert, (ip,))
            self.conexion.commit()
            
            cursor.close()
            logger.info(f"IP {ip} registrada en base de datos")
            return True
            
        except Error as e:
            logger.error(f"Error registrando IP: {e}")
            return False
    
    def desconectar(self):
        """Cierra la conexión con la base de datos"""
        if self.conexion and self.conexion.is_connected():
            self.conexion.close()
            logger.info("Conexión a base de datos cerrada")
