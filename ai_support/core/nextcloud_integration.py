"""
Integración con Nextcloud para cargar y gestionar archivos.
"""

import os
import requests
from typing import Optional, List, Dict
from urllib.parse import urljoin


def nextcloud_enabled() -> bool:
    """Verifica si Nextcloud está configurado."""
    return bool(
        os.getenv("NEXTCLOUD_URL") and 
        os.getenv("NEXTCLOUD_USERNAME") and
        os.getenv("NEXTCLOUD_PASSWORD")
    )


def get_nextcloud_config() -> dict:
    """Retorna configuración de Nextcloud."""
    return {
        "url": os.getenv("NEXTCLOUD_URL", "").rstrip("/"),
        "username": os.getenv("NEXTCLOUD_USERNAME", ""),
        "password": os.getenv("NEXTCLOUD_PASSWORD", ""),
        "webdav_path": os.getenv("NEXTCLOUD_WEBDAV_PATH", "/remote.php/dav/files"),
    }


def list_nextcloud_files(
    path: str = "",
    file_extensions: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """Lista archivos en Nextcloud.
    
    Args:
        path: Ruta relativa en Nextcloud (por defecto raíz del usuario)
        file_extensions: Lista de extensiones a filtrar (ej: ['.xlsx', '.xls'])
    
    Returns:
        Lista de diccionarios con información de archivos:
        [{"name": "archivo.xlsx", "path": "/path/to/archivo.xlsx", "size": 12345, "modified": "..."}]
    """
    config = get_nextcloud_config()
    if not nextcloud_enabled():
        return []
    
    # Construir URL de WebDAV
    webdav_url = urljoin(
        config["url"],
        f"{config['webdav_path']}/{config['username']}/{path}"
    )
    
    try:
        # Realizar petición PROPFIND para listar archivos
        response = requests.request(
            "PROPFIND",
            webdav_url,
            auth=(config["username"], config["password"]),
            headers={"Depth": "1"},
            timeout=10
        )
        response.raise_for_status()
        
        # Parsear respuesta XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        files = []
        for response_elem in root.findall(".//{DAV:}response"):
            href_elem = response_elem.find("{DAV:}href")
            if href_elem is None:
                continue
                
            href = href_elem.text
            # Extraer nombre del archivo
            file_path = href.split(f"{config['username']}/")[-1] if f"{config['username']}/" in href else href
            file_name = os.path.basename(file_path)
            
            # Saltar el directorio actual
            if not file_name or file_path.endswith("/"):
                continue
            
            # Filtrar por extensión si se especifica
            if file_extensions:
                if not any(file_name.lower().endswith(ext.lower()) for ext in file_extensions):
                    continue
            
            # Obtener metadata
            size_elem = response_elem.find(".//{DAV:}getcontentlength")
            modified_elem = response_elem.find(".//{DAV:}getlastmodified")
            
            files.append({
                "name": file_name,
                "path": file_path,
                "size": int(size_elem.text) if size_elem is not None and size_elem.text else 0,
                "modified": modified_elem.text if modified_elem is not None else "",
                "url": href
            })
        
        return files
    
    except Exception as e:
        print(f"Error al listar archivos de Nextcloud: {e}")
        return []


def download_nextcloud_file(file_path: str) -> Optional[bytes]:
    """Descarga un archivo desde Nextcloud.
    
    Args:
        file_path: Ruta del archivo en Nextcloud
    
    Returns:
        Contenido del archivo en bytes, o None si hay error
    """
    config = get_nextcloud_config()
    if not nextcloud_enabled():
        return None
    
    # Construir URL de descarga
    download_url = urljoin(
        config["url"],
        f"{config['webdav_path']}/{config['username']}/{file_path}"
    )
    
    try:
        response = requests.get(
            download_url,
            auth=(config["username"], config["password"]),
            timeout=30
        )
        response.raise_for_status()
        return response.content
    
    except Exception as e:
        print(f"Error al descargar archivo de Nextcloud: {e}")
        return None


def get_nextcloud_share_link(file_path: str, password: Optional[str] = None) -> Optional[str]:
    """Crea un enlace de compartición público para un archivo.
    
    Args:
        file_path: Ruta del archivo en Nextcloud
        password: Contraseña opcional para proteger el enlace
    
    Returns:
        URL del enlace público, o None si hay error
    """
    config = get_nextcloud_config()
    if not nextcloud_enabled():
        return None
    
    share_url = urljoin(config["url"], "/ocs/v2.php/apps/files_sharing/api/v1/shares")
    
    data = {
        "path": f"/{file_path}",
        "shareType": 3,  # Public link
    }
    
    if password:
        data["password"] = password
    
    try:
        response = requests.post(
            share_url,
            auth=(config["username"], config["password"]),
            headers={"OCS-APIRequest": "true"},
            data=data,
            timeout=10
        )
        response.raise_for_status()
        
        # Parsear respuesta XML
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        url_elem = root.find(".//url")
        if url_elem is not None:
            return url_elem.text
        
        return None
    
    except Exception as e:
        print(f"Error al crear enlace de Nextcloud: {e}")
        return None


def upload_to_nextcloud(file_content: bytes, file_path: str) -> bool:
    """Sube un archivo a Nextcloud.
    
    Args:
        file_content: Contenido del archivo en bytes
        file_path: Ruta destino en Nextcloud
    
    Returns:
        True si se subió correctamente, False en caso contrario
    """
    config = get_nextcloud_config()
    if not nextcloud_enabled():
        return False
    
    upload_url = urljoin(
        config["url"],
        f"{config['webdav_path']}/{config['username']}/{file_path}"
    )
    
    try:
        response = requests.put(
            upload_url,
            auth=(config["username"], config["password"]),
            data=file_content,
            timeout=30
        )
        response.raise_for_status()
        return True
    
    except Exception as e:
        print(f"Error al subir archivo a Nextcloud: {e}")
        return False
