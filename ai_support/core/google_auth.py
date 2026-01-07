"""Autenticación Google (OAuth2 / OpenID Connect).

Objetivo: permitir que el sistema use un usuario autenticado (email) como `user_id`.
Se valida dominio permitido (por defecto `uchile.cl`).

Configuración por variables de entorno:
- AI_SUPPORT_GOOGLE_CLIENT_ID
- AI_SUPPORT_GOOGLE_CLIENT_SECRET
- AI_SUPPORT_GOOGLE_REDIRECT_URI
- AI_SUPPORT_GOOGLE_ALLOWED_DOMAIN (default: uchile.cl)

Nota: el redirect debe estar registrado en Google Cloud Console (OAuth client).
"""

from __future__ import annotations

import os
import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


_GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"


def google_auth_enabled() -> bool:
    raw = os.getenv("AI_SUPPORT_ENABLE_GOOGLE_AUTH")
    if raw is None:
        return False
    enabled = raw.strip().lower() in {"1", "true", "yes", "y", "on"}
    if not enabled:
        return False
    return bool(os.getenv("AI_SUPPORT_GOOGLE_CLIENT_ID") and os.getenv("AI_SUPPORT_GOOGLE_CLIENT_SECRET"))


def google_allowed_domain() -> str:
    return (os.getenv("AI_SUPPORT_GOOGLE_ALLOWED_DOMAIN") or "uchile.cl").strip().lower()


def google_redirect_uri() -> Optional[str]:
    uri = os.getenv("AI_SUPPORT_GOOGLE_REDIRECT_URI")
    if not uri:
        return None
    return uri.strip()


def build_google_auth_url(*, state: str) -> str:
    client_id = os.getenv("AI_SUPPORT_GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = google_redirect_uri()
    if not client_id or not redirect_uri:
        raise ValueError("Falta AI_SUPPORT_GOOGLE_CLIENT_ID o AI_SUPPORT_GOOGLE_REDIRECT_URI")

    allowed_domain = google_allowed_domain()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
        "state": state,
        # Hint de dominio (no es enforcement, solo sugerencia)
        "hd": allowed_domain,
    }

    return _GOOGLE_AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(*, code: str) -> Dict[str, Any]:
    """Intercambia `code` por tokens.

    Retorna dict que usualmente incluye: access_token, id_token, expires_in, scope, token_type.
    """

    client_id = os.getenv("AI_SUPPORT_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("AI_SUPPORT_GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = google_redirect_uri()

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError("Falta configuración Google OAuth (client_id/client_secret/redirect_uri)")

    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        _GOOGLE_TOKEN_ENDPOINT,
        method="POST",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        raise ValueError(f"Error intercambiando code por tokens: {e}")


def verify_id_token_and_get_email(*, raw_id_token: str) -> str:
    """Valida el id_token y retorna el email.

    Enforce: email verificado + dominio permitido.
    """

    client_id = os.getenv("AI_SUPPORT_GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise ValueError("Falta AI_SUPPORT_GOOGLE_CLIENT_ID")

    # Verificación vía endpoint oficial tokeninfo.
    # Esto valida firma/expiración y retorna claims.
    url = _GOOGLE_TOKENINFO_ENDPOINT + "?" + urllib.parse.urlencode({"id_token": raw_id_token})
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Token inválido: {e}")

    aud = (payload.get("aud") or "").strip()
    if aud != client_id:
        raise ValueError("Token inválido (audience no coincide)")

    email = (payload.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Token no contiene email")

    # tokeninfo entrega email_verified como string "true"/"false" a veces
    email_verified = payload.get("email_verified")
    if isinstance(email_verified, str):
        email_verified = email_verified.strip().lower() == "true"
    if email_verified is not True:
        raise ValueError("Email no verificado por Google")

    allowed_domain = google_allowed_domain()
    if not email.endswith("@" + allowed_domain):
        raise ValueError(f"Email no permitido (debe ser @{allowed_domain})")

    return email
