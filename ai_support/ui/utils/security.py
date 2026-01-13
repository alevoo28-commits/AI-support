"""
Módulo de seguridad - Validación de contenido peligroso.
"""

# Keywords prohibidas por seguridad y ética
FORBIDDEN_KEYWORDS = [
    "hackear",
    "hack",
    "sql injection",
    "inyección sql",
    "bypass",
    "exploit",
    "ataque",
    "crackear",
    "phishing",
    "obtener contraseña",
    "password leak",
    "robar datos",
    "malware",
    "virus",
    "script malicioso",
    "evadir seguridad",
    "eludir seguridad",
    "saltarse seguridad",
    "acceder sin permiso",
    "acceso no autorizado",
    "piratear",
    "piratería",
    "rootkit",
    "keylogger",
    "payload",
    "reverse shell",
    "escalar privilegios",
    "privilege escalation",
]


def contiene_peligro(texto: str) -> bool:
    """
    Verifica si un texto contiene keywords peligrosas.
    
    Args:
        texto: Texto a verificar
    
    Returns:
        bool: True si contiene keywords peligrosas
    """
    texto_l = texto.lower()
    return any(palabra in texto_l for palabra in FORBIDDEN_KEYWORDS)
