from __future__ import annotations

import os
import sys
from typing import Optional


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def main() -> int:
    """Entry point to run the remote agent as a normal process.

    This is designed to be packaged as a standalone .exe (PyInstaller), so client PCs
    don't need Python installed.
    """

    try:
        import uvicorn  # type: ignore
    except Exception as e:
        print(f"ERROR: uvicorn no disponible: {e}", file=sys.stderr)
        return 2

    host = _env("AI_SUPPORT_REMOTE_AGENT_HOST", "0.0.0.0") or "0.0.0.0"
    port_raw = _env("AI_SUPPORT_REMOTE_AGENT_PORT", "8765") or "8765"
    try:
        port = int(port_raw)
    except Exception:
        port = 8765

    # Token requerido por client_app.py (X-AI-SUPPORT-TOKEN)
    token = _env("AI_SUPPORT_REMOTE_AGENT_TOKEN")
    if not token:
        print(
            "ERROR: Falta AI_SUPPORT_REMOTE_AGENT_TOKEN. Define un token para proteger el agente.",
            file=sys.stderr,
        )
        return 2

    uvicorn.run(
        "ai_support.remote_agent.client_app:app",
        host=host,
        port=port,
        log_level=_env("AI_SUPPORT_REMOTE_AGENT_LOG_LEVEL", "info") or "info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
