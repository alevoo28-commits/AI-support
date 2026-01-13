from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path


def is_windows_admin() -> bool:
    """Return True if current process has admin rights (Windows only)."""
    if os.name != "nt":
        return False
    try:
        import ctypes  # pylint: disable=import-outside-toplevel

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def build_streamlit_run_command() -> list[str]:
    """Build the command to run the app via streamlit from repo root."""
    # Repo root is two levels up from ai_support/ui
    root = Path(__file__).resolve().parents[2]
    entry = root / "sistema_completo_agentes.py"

    python_exe = sys.executable
    if not python_exe:
        python_exe = "python"

    # Use `-m streamlit` to ensure correct env.
    return [python_exe, "-m", "streamlit", "run", str(entry)]


def restart_streamlit_elevated() -> None:
    """Start a new elevated Streamlit process via UAC prompt.

    This cannot bypass UAC; it triggers the standard consent dialog.
    """

    cmd = build_streamlit_run_command()

    # PowerShell Start-Process -Verb RunAs triggers UAC.
    # Use -ArgumentList to preserve quoting.
    ps = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        (
            "Start-Process -Verb RunAs -FilePath "
            + _ps_quote(cmd[0])
            + " -ArgumentList "
            + _ps_quote(" ".join(_quote_args_for_cmd(cmd[1:])))
        ),
    ]

    # Fire-and-forget; current Streamlit keeps running until user closes tab.
    subprocess.Popen(ps, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ps_quote(value: str) -> str:
    # Single-quote for PowerShell, escape single quotes by doubling.
    v = str(value).replace("'", "''")
    return f"'{v}'"


def _quote_args_for_cmd(args: list[str]) -> list[str]:
    """Best-effort quoting for Windows command line."""
    out: list[str] = []
    for a in args:
        s = str(a)
        if not s:
            out.append('""')
            continue
        if any(ch in s for ch in [' ', '\t', '"']):
            s = s.replace('"', '\\"')
            out.append(f'"{s}"')
        else:
            out.append(s)
    return out
