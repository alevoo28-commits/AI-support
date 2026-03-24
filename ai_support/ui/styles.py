"""
Estilos CSS modernos para la aplicación Streamlit.
Separado en módulo para mantener el código limpio y mantenible.
Incluye soporte para múltiples temas (light, dark, high-contrast).
"""

def get_custom_styles(theme: str = "light") -> str:
    """
    Retorna el CSS personalizado modernizado para toda la aplicación.
    
    Args:
        theme (str): Tema a usar. Opciones: "light" (default), "dark", "high-contrast"
    
    Returns:
        str: CSS completo encapsulado en <style> tags
    """
    
    # Definir paletas de colores por tema
    themes = {
        "light": {
            "primary": "#0ea5e9",
            "primary-dark": "#0284c7",
            "secondary": "#06b6d4",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "bg-light": "#f9fafb",
            "bg-gray": "#f3f4f6",
            "text-primary": "#1f2937",
            "text-secondary": "#6b7280",
            "border": "#e5e7eb",
            "app-bg": "linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%)",
            "sidebar-bg": "linear-gradient(180deg, #ffffff 0%, #f9fafb 100%)",
            "button-secondary-bg": "linear-gradient(135deg, #e0e7ff 0%, #f0f4ff 100%)",
            "button-secondary-color": "#1e293b",
            "input-bg": "#ffffff",
            "code-bg": "#1e293b",
            "code-color": "#e2e8f0",
        },
        "dark": {
            "primary": "#0ea5e9",
            "primary-dark": "#0284c7",
            "secondary": "#06b6d4",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
            "bg-light": "#0f172a",
            "bg-gray": "#1e293b",
            "text-primary": "#f1f5f9",
            "text-secondary": "#cbd5e1",
            "border": "#334155",
            "app-bg": "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
            "sidebar-bg": "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
            "button-secondary-bg": "linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)",
            "button-secondary-color": "#e0e7ff",
            "input-bg": "#1e293b",
            "code-bg": "#0f172a",
            "code-color": "#e2e8f0",
        },
        "high-contrast": {
            "primary": "#0052cc",
            "primary-dark": "#003d99",
            "secondary": "#0066ff",
            "success": "#008000",
            "warning": "#cc6600",
            "danger": "#cc0000",
            "bg-light": "#ffffff",
            "bg-gray": "#f0f0f0",
            "text-primary": "#000000",
            "text-secondary": "#333333",
            "border": "#000000",
            "app-bg": "#ffffff",
            "sidebar-bg": "#f0f0f0",
            "button-secondary-bg": "#ffffff",
            "button-secondary-color": "#000000",
            "input-bg": "#ffffff",
            "code-bg": "#000000",
            "code-color": "#ffffff",
        }
    }
    
    # Usar tema especificado o default
    colors = themes.get(theme, themes["light"])
    
    # Construir CSS dinámicamente
    css = f"""
    <style>
    /* ═════════════════════════════════════════════════════════════
       DISEÑO MODERNO PROFESIONAL 2026
       Tema: {theme.upper()}
       ═════════════════════════════════════════════════════════════ */
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {{ 
        font-family: 'Inter', sans-serif;
        transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
    }}

    /* ─── COLORES MODERNOS (DINÁMICOS POR TEMA) ─── */
    :root {{
        --primary: {colors['primary']};
        --primary-dark: {colors['primary-dark']};
        --secondary: {colors['secondary']};
        --success: {colors['success']};
        --warning: {colors['warning']};
        --danger: {colors['danger']};
        --bg-light: {colors['bg-light']};
        --bg-gray: {colors['bg-gray']};
        --text-primary: {colors['text-primary']};
        --text-secondary: {colors['text-secondary']};
        --border: {colors['border']};
    }}

    /* ─── FONDO PRINCIPAL ─── */
    .stApp {{ 
        background: {colors['app-bg']} !important; 
    }}

    [data-testid="stAppViewContainer"] > .main {{ 
        background: {colors['app-bg']} !important; 
    }}

    .block-container {{ 
        background: transparent !important;
        padding-top: 2.5rem !important;
        max-width: 1400px !important;
    }}

    /* ─── SIDEBAR MODERNO ─── */
    [data-testid="stSidebar"] {{
        background: {colors['sidebar-bg']} !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: 2px 0 12px rgba(0,0,0,0.05);
    }}

    [data-testid="stSidebar"] .stMarkdown h3 {{
        color: var(--primary) !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
        margin-top: 1.5rem !important;
    }}

    /* ─── TEXTO GENERAL ─── */
    html, body, p, span, div, label {{ 
        color: var(--text-primary) !important;
    }}

    h1, h2, h3, h4 {{ 
        color: var(--text-primary) !important; 
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}

    h1 {{ font-size: 2.2rem; }}
    h2 {{ font-size: 1.8rem; margin-top: 1.5rem; }}
    h3 {{ font-size: 1.4rem; }}

    /* ─── BOTONES PRIMARIOS (CYAN MODERNO) ─── */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        padding: 0.65rem 1.5rem !important;
        margin-bottom: 8px !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(14, 165, 233, 0.35) !important;
    }}

    .stButton > button[kind="primary"]:active {{
        transform: translateY(0px) !important;
    }}

    /* ─── BOTONES SECUNDARIOS ─── */
    .stButton > button[kind="secondary"] {{
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.25s ease !important;
        margin-bottom: 8px !important;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.25) !important;
    }}
    
    .stButton > button[kind="secondary"]:hover {{
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35) !important;
        transform: translateY(-2px) !important;
        color: #ffffff !important;
    }}

    /* ─── INPUTS Y TEXTAREAS ─── */
    input, textarea, select {{
        background: {colors['input-bg']} !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        transition: all 0.25s ease !important;
    }}

    input:focus, textarea:focus, select:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1) !important;
        outline: none !important;
    }}

    /* ─── CHAT INPUT ─── */
    [data-testid="stChatInput"] > div {{
        background: {colors['input-bg']} !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    }}

    [data-testid="stChatInput"] textarea {{ 
        color: var(--text-primary) !important; 
    }}

    /* ─── CHAT MESSAGES ─── */
    [data-testid="stChatMessage"] {{
        background: {colors['input-bg']} !important;
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        margin-bottom: 10px !important;
        animation: slideIn 0.3s ease-out;
    }}

    /* ─── ALERTAS CON COLORES SUAVES ─── */
    .stSuccess, .element-container .stSuccess > div {{
        background: #ecfdf5 !important;
        border-left: 4px solid var(--success) !important;
        border-radius: 8px !important;
        color: #065f46 !important;
    }}

    .stWarning, .element-container .stWarning > div {{
        background: #fffbeb !important;
        border-left: 4px solid var(--warning) !important;
        border-radius: 8px !important;
        color: #78350f !important;
    }}

    .stError, .element-container .stError > div {{
        background: #fef2f2 !important;
        border-left: 4px solid var(--danger) !important;
        border-radius: 8px !important;
        color: #7f1d1d !important;
    }}

    .stInfo, .element-container .stInfo > div {{
        background: #eff6ff !important;
        border-left: 4px solid var(--primary) !important;
        border-radius: 8px !important;
        color: #0c4a6e !important;
    }}

    /* ─── EXPANDERS Y COLAPSABLES ─── */
    [data-testid="stExpander"] {{
        background: {colors['input-bg']} !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
        overflow: hidden !important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }}

    /* ── Métricas ── */
    [data-testid="stMetricValue"] {{ color: var(--primary) !important; font-weight: 700 !important; }}
    [data-testid="stMetricLabel"] {{ color: var(--text-secondary) !important; font-size: 0.85rem !important; }}

    /* ── Divider ── */
    hr {{ border-color: var(--border) !important; }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-gray); }}
    ::-webkit-scrollbar-thumb {{ background: var(--primary); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--primary-dark); }}

    /* ── Caption ── */
    .stCaption, small {{ color: var(--text-secondary) !important; font-size: 0.82rem !important; }}

    /* ── Botones de navegación en sidebar ── */
    .nav-button {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        margin: 4px 0 !important;
        font-weight: 600 !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 2px 6px rgba(14, 165, 233, 0.2) !important;
    }}
    .nav-button:hover {{
        background: linear-gradient(135deg, var(--primary-dark) 0%, #0369a1 100%) !important;
        transform: translateX(2px) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.35) !important;
    }}

    /* ── Radio ── */
    .stRadio > div {{ gap: 8px; }}
    .stRadio > label {{ 
        margin-bottom: 12px !important; 
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }}
    .stRadio label {{
        background: linear-gradient(135deg, {colors['button-secondary-bg']} 0%, {colors['input-bg']} 100%) !important;
        border: 1.5px solid var(--primary) !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        margin-bottom: 6px !important;
        cursor: pointer !important;
    }}
    .stRadio label:hover {{ 
        border-color: var(--primary-dark) !important; 
        background: linear-gradient(135deg, var(--primary) 0%, #0895ca 100%) !important;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3) !important;
        transform: translateY(-2px) !important;
    }}

    /* ── Checkbox ── */
    .stCheckbox label span {{ color: var(--text-primary) !important; }}

    /* ── Selectbox ── */
    .stSelectbox > div > div {{ 
        background: {colors['input-bg']} !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    .stSelectbox > div > div:focus {{
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1) !important;
    }}

    /* ── Código ── */
    code, pre {{ 
        background: {colors['code-bg']} !important; 
        color: {colors['code-color']} !important;
        border-radius: 6px !important;
        padding: 2px 6px !important;
    }}

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {{ border-radius: 10px !important; overflow: hidden !important; }}
    
    /* ── Animaciones ── */
    @keyframes slideIn {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    </style>
    """
    
    return css


def get_available_themes() -> list[str]:
    """
    Retorna la lista de temas disponibles.
    
    Returns:
        list[str]: Lista de temas: ["light", "dark", "high-contrast"]
    """
    return ["light", "dark", "high-contrast"]


def apply_theme_in_app(theme: str = "light") -> None:
    """
    Aplica un tema en la aplicación Streamlit.
    
    Nota: Debe llamarse ANTES de cualquier otro contenido Streamlit.
    
    Args:
        theme (str): Tema a aplicar ("light", "dark", "high-contrast")
    
    Example:
        >>> import streamlit as st
        >>> from ai_support.ui.styles import apply_theme_in_app
        >>> apply_theme_in_app("dark")
        >>> st.write("Contenido con tema oscuro...")
    """
    try:
        import streamlit as st
        st.markdown(get_custom_styles(theme=theme), unsafe_allow_html=True)
    except ImportError:
        # Si Streamlit no está disponible, solo ignorar
        pass

