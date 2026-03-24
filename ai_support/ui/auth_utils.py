"""
Utilidades de autenticación, rate limiting y auditoría.

Este módulo maneja:
- Límites de rate limiting por función
- Verificación y registro de intentos fallidos
- Generación de claves de identidad
- Auditoría de eventos de autenticación
"""

import os
import time
import threading
import json
from ai_support.core.logging_utils import log_event


# ── Global state para rate limiting ────────────────────────────────────────
_AUTH_RATE_LIMIT_LOCK = threading.Lock()
_AUTH_RATE_LIMIT_STATE: dict[str, list[float]] = {}
_AUTH_LOCK_UNTIL: dict[str, float] = {}


def env_int(name: str, default: int) -> int:
    """Lee un valor entero desde variable de entorno."""
    try:
        value = int((os.getenv(name) or "").strip())
        return value if value > 0 else default
    except Exception:
        return default


def auth_limits() -> tuple[int, int, int]:
    """Retorna (max_attempts, window_seconds, lock_seconds) desde envvars."""
    max_attempts = env_int("AI_SUPPORT_AUTH_MAX_ATTEMPTS", 5)
    window_seconds = env_int("AI_SUPPORT_AUTH_WINDOW_SECONDS", 300)
    lock_seconds = env_int("AI_SUPPORT_AUTH_LOCK_SECONDS", 900)
    return max_attempts, window_seconds, lock_seconds


def auth_is_blocked(key: str) -> tuple[bool, int]:
    """Verifica si una identidad está bloqueada por rate limiting.
    
    Retorna (is_blocked, remaining_seconds).
    """
    now = time.time()
    with _AUTH_RATE_LIMIT_LOCK:
        lock_until = _AUTH_LOCK_UNTIL.get(key, 0.0)
        if lock_until > now:
            return True, int(lock_until - now)
        if key in _AUTH_LOCK_UNTIL:
            _AUTH_LOCK_UNTIL.pop(key, None)
    return False, 0


def auth_register_failure(key: str) -> tuple[bool, int]:
    """Registra un intento fallido y aplica rate limiting si es necesario.
    
    Retorna (newly_blocked, lock_seconds) - True si acaba de bloquearse.
    """
    now = time.time()
    max_attempts, window_seconds, lock_seconds = auth_limits()
    with _AUTH_RATE_LIMIT_LOCK:
        attempts = _AUTH_RATE_LIMIT_STATE.get(key, [])
        cutoff = now - window_seconds
        attempts = [ts for ts in attempts if ts >= cutoff]
        attempts.append(now)
        _AUTH_RATE_LIMIT_STATE[key] = attempts
        if len(attempts) >= max_attempts:
            _AUTH_LOCK_UNTIL[key] = now + lock_seconds
            _AUTH_RATE_LIMIT_STATE[key] = []
            return True, lock_seconds
    return False, 0


def auth_register_success(key: str) -> None:
    """Limpia el estado de intentos fallidos para una identidad (login exitoso)."""
    with _AUTH_RATE_LIMIT_LOCK:
        _AUTH_RATE_LIMIT_STATE.pop(key, None)
        _AUTH_LOCK_UNTIL.pop(key, None)


def auth_identity_key(email: str | None, session_key: str) -> str:
    """Genera un key único para identificar un usuario en rate limiting.
    
    Prefiere email normalizado, fallback a session_key.
    """
    normalized = (email or "").strip().lower()
    if normalized:
        return f"email:{normalized}"
    return f"session:{session_key}"


def audit_auth_event(
    email: str | None,
    result: str,
    reason: str,
    department_id: int | None = None,
    department_name: str | None = None,
) -> None:
    """Registra un evento de autenticación en los logs para auditoría."""
    payload = {
        "event": "auth_decision",
        "email": (email or "").strip().lower() or None,
        "result": result,
        "reason": reason,
        "department_id": department_id,
        "department_name": department_name,
    }
    try:
        log_event(json.dumps(payload, ensure_ascii=False), level="info")
    except Exception:
        pass
