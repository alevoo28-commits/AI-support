"""
Integración con OnlyOffice Document Server para visualizar y editar Excel con IA.
"""

import os
import jwt
import hashlib
from datetime import datetime
from typing import Optional


def onlyoffice_enabled() -> bool:
    """Verifica si OnlyOffice está configurado."""
    return bool(
        os.getenv("ONLYOFFICE_API_URL") and 
        os.getenv("ONLYOFFICE_JWT_SECRET")
    )


def get_onlyoffice_config() -> dict:
    """Retorna configuración de OnlyOffice."""
    return {
        "api_url": os.getenv("ONLYOFFICE_API_URL", "").rstrip("/"),
        "jwt_secret": os.getenv("ONLYOFFICE_JWT_SECRET", ""),
    }


def generate_onlyoffice_config(
    document_url: str,
    filename: str,
    filetype: str,
    key: Optional[str] = None,
    user_id: str = "user",
    user_name: str = "User",
    mode: str = "view",  # "view" o "edit"
) -> dict:
    """Genera configuración para el editor de OnlyOffice.
    
    Args:
        document_url: URL pública del documento
        filename: Nombre del archivo
        filetype: Extensión sin punto (xlsx, docx, etc.)
        key: Clave única del documento (se genera automática si no se provee)
        user_id: ID del usuario
        user_name: Nombre del usuario
        mode: "view" o "edit"
    
    Returns:
        Dict con configuración completa para OnlyOffice
    """
    config = get_onlyoffice_config()
    
    if not key:
        # Generar key basada en URL + timestamp
        key = hashlib.sha256(
            f"{document_url}_{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:20]
    
    # Configuración base según documentación oficial
    editor_config = {
        "documentType": get_document_type(filetype),
        "document": {
            "fileType": filetype.lower(),
            "key": key,
            "title": filename,
            "url": document_url,
        },
        "editorConfig": {
            "mode": mode,
            "user": {
                "id": user_id,
                "name": user_name,
            },
            "customization": {
                "autosave": True,
                "forcesave": True,
            },
        },
        "type": "desktop",
        "height": "100%",
        "width": "100%",
    }
    
    # Firmar con JWT si está configurado
    if config["jwt_secret"]:
        token = jwt.encode(
            editor_config,
            config["jwt_secret"],
            algorithm="HS256"
        )
        editor_config["token"] = token
    
    return editor_config


def get_document_type(filetype: str) -> str:
    """Determina el tipo de documento para OnlyOffice según la documentación oficial.
    
    Tipos soportados:
    - word: documentos de texto
    - cell: hojas de cálculo  
    - slide: presentaciones
    - pdf: documentos PDF
    """
    # Hojas de cálculo (cell)
    spreadsheet = {"csv", "et", "ett", "fods", "numbers", "ods", "ots", "sxc", 
                   "xls", "xlsb", "xlsm", "xlsx", "xlt", "xltm", "xltx", "xml"}
    
    # Documentos de texto (word)
    text = {"doc", "docm", "docx", "dot", "dotm", "dotx", "epub", "fb2", "fodt", 
            "hml", "htm", "html", "md", "hwp", "hwpx", "mht", "mhtml", "odt", 
            "ott", "pages", "rtf", "stw", "sxw", "txt", "wps", "wpt"}
    
    # Presentaciones (slide)
    presentation = {"dps", "dpt", "fodp", "key", "odg", "odp", "otp", "pot", 
                    "potm", "potx", "pps", "ppsm", "ppsx", "ppt", "pptm", "pptx", "sxi"}
    
    # PDF
    pdf = {"djvu", "oxps", "pdf", "xps"}
    
    filetype_lower = filetype.lower()
    
    if filetype_lower in spreadsheet:
        return "cell"
    elif filetype_lower in text:
        return "word"
    elif filetype_lower in presentation:
        return "slide"
    elif filetype_lower in pdf:
        return "pdf"
    
    # Por defecto, asumir word
    return "word"


def generate_onlyoffice_html(config: dict, container_id: str = "onlyoffice-editor") -> str:
    """Genera HTML para incrustar el editor de OnlyOffice.
    
    Args:
        config: Configuración generada por generate_onlyoffice_config
        container_id: ID del contenedor HTML
    
    Returns:
        HTML completo con el editor
    """
    onlyoffice_config = get_onlyoffice_config()
    api_url = onlyoffice_config["api_url"]
    
    import json
    config_json = json.dumps(config, indent=2)
    
    html = f"""
    <style>
        #{container_id} {{
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .onlyoffice-status {{
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
        }}
        .status-loading {{
            background: #fff3cd;
            border: 1px solid #ffc107;
        }}
        .status-success {{
            background: #d4edda;
            border: 1px solid #28a745;
        }}
        .status-error {{
            background: #f8d7da;
            border: 1px solid #dc3545;
        }}
    </style>
    
    <div id="onlyoffice-status" class="onlyoffice-status status-loading">
        📄 Cargando OnlyOffice Document Server...
    </div>
    
    <div id="{container_id}"></div>
    
    <script type="text/javascript" src="{api_url}/web-apps/apps/api/documents/api.js"></script>
    <script type="text/javascript">
        console.log("=== OnlyOffice Configuration ===");
        console.log({config_json});
        console.log("================================");
        
        var statusEl = document.getElementById("onlyoffice-status");
        
        try {{
            var docEditor = new DocsAPI.DocEditor("{container_id}", {{
                ...{config_json},
                events: {{
                    onAppReady: function() {{
                        console.log("✓ OnlyOffice: App Ready");
                        statusEl.className = "onlyoffice-status status-success";
                        statusEl.innerHTML = "✓ OnlyOffice cargado correctamente";
                    }},
                    onDocumentReady: function() {{
                        console.log("✓ OnlyOffice: Document Ready");
                    }},
                    onError: function(event) {{
                        console.error("✗ OnlyOffice Error:", event);
                        statusEl.className = "onlyoffice-status status-error";
                        statusEl.innerHTML = "✗ Error al cargar documento: " + JSON.stringify(event);
                    }},
                    onWarning: function(event) {{
                        console.warn("⚠ OnlyOffice Warning:", event);
                    }}
                }}
            }});
            
            console.log("✓ OnlyOffice Editor initialized");
            
        }} catch(error) {{
            console.error("✗ Failed to initialize OnlyOffice:", error);
            statusEl.className = "onlyoffice-status status-error";
            statusEl.innerHTML = "✗ Error al inicializar OnlyOffice: " + error.message;
        }}
    </script>
    
    <div style="margin-top: 10px; padding: 10px; background: #e7f3ff; border-radius: 4px; font-size: 12px;">
        <strong>💡 Consejos:</strong><br>
        • Abre la consola del navegador (F12) para ver logs detallados<br>
        • Verifica que la URL del documento sea accesible públicamente<br>
        • El servidor OnlyOffice debe poder acceder a la URL del documento
    </div>
    """
    
    return html
