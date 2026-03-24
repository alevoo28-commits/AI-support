# 🎨 Guía de Personalización de Colores - Temas Alternativos 2026

## 📋 Paletas Prediseñadas

### **PALETA 1: ÍNDIGO MODERNO (Por Defecto)**
```css
--primary: #6366f1;           /* Índigo vibrante */
--primary-dark: #4f46e5;      /* Índigo oscuro */
--secondary: #ec4899;         /* Rosa neón */
--success: #10b981;           /* Verde esmeralda */
--warning: #f59e0b;           /* Ámbar */
--error: #ef4444;             /* Rojo */
--dark-bg: #0f172a;           /* Negro azulado profundo */
--dark-surface: #1e293b;      /* Gris azul */
```
**Mejor para:** Apps profesionales, SaaS, Tech

---

### **PALETA 2: CIBERFY (Magenta + Cian)**
```css
--primary: #d946ef;           /* Magenta puro */
--primary-dark: #c026d3;      /* Magenta oscuro */
--secondary: #0891b2;         /* Cian */
--success: #06b6d4;           /* Cyan claro */
--warning: #eab308;           /* Amarillo */
--error: #e11d48;             /* Rosa rojo */
--dark-bg: #0a0a0a;           /* Negro puro */
--dark-surface: #18181b;      /* Gris muy oscuro */
```
**Mejor para:** Gaming, creativo, energético

---

### **PALETA 3: OCEAN (Azul + Turquesa)**
```css
--primary: #0369a1;           /* Azul océano */
--primary-dark: #0c4a6e;      /* Azul profundo */
--secondary: #0891b2;         /* Turquesa */
--success: #0891b2;           /* Cyan */
--warning: #f59e0b;           /* Ámbar */
--error: #dc2626;             /* Rojo intenso */
--dark-bg: #020617;           /* Negro oscuro */
--dark-surface: #1e293b;      /* Gris azul */
```
**Mejor para:** Fintech, banca, confianza

---

### **PALETA 4: SUNSET (Naranja + Rosa)**
```css
--primary: #ea580c;           /* Naranja intenso */
--primary-dark: #c2410c;      /* Naranja oscuro */
--secondary: #f97316;         /* Naranja claro */
--success: #65a30d;           /* Verde lima */
--warning: #d97706;           /* Ámbar naranja */
--error: #dc2626;             /* Rojo vivo */
--dark-bg: #1c1917;           /* Marrón oscuro */
--dark-surface: #292524;      /* Gris cálido */
```
**Mejor para:** Creatividad, educación, energía

---

### **PALETA 5: FOREST (Verde + Azul)**
```css
--primary: #059669;           /* Verde bosque */
--primary-dark: #047857;      /* Verde profundo */
--secondary: #0369a1;         /* Azul */
--success: #10b981;           /* Verde éxito */
--warning: #d97706;           /* Ámbar */
--error: #eb2754;             /* Rosa error */
--dark-bg: #0c2e1f;           /* Verde muy oscuro */
--dark-surface: #1f3a34;      /* Verde gris */
```
**Mejor para:** Sostenibilidad, salud, naturaleza

---

### **PALETA 6: MINIMAL (Monocromática)**
```css
--primary: #7c3aed;           /* Púrpura */
--primary-dark: #6d28d9;      /* Púrpura oscuro */
--secondary: #6b7280;         /* Gris neutral */
--success: #8b5cf6;           /* Púrpura claro */
--warning: #9ca3af;           /* Gris */
--error: #a1a1aa;             /* Gris error */
--dark-bg: #18181b;           /* Negro blanco */
--dark-surface: #27272a;      /* Gris oscuro */
```
**Mejor para:** Minimalismo, corporativo, elegancia

---

## 🔧 Cómo Cambiar de Paleta

### **Método 1: Editar CSS Directamente**

En `streamlit_app_modern.py`, encuentra `inject_modern_css()` y localiza:

```python
css = """
<style>
:root {
    --primary: #6366f1;           /* <- Cambiar aquí */
    --primary-dark: #4f46e5;
    --secondary: #ec4899;         /* <- Y aquí */
    /* ... resto de variables ... */
}
```

**Reemplaza todos los valores `--primary`, `--secondary`, etc. con tu paleta elegida**

---

### **Método 2: Crear Función de Temas**

```python
THEMES = {
    "indigo_moderno": {
        "primary": "#6366f1",
        "secondary": "#ec4899",
        "success": "#10b981",
        "dark_bg": "#0f172a",
        "dark_surface": "#1e293b",
        "text_primary": "#f9fafb",
        "text_secondary": "#cbd5e1",
    },
    "ciberfy": {
        "primary": "#d946ef",
        "secondary": "#0891b2",
        "success": "#06b6d4",
        "dark_bg": "#0a0a0a",
        "dark_surface": "#18181b",
        "text_primary": "#f9fafb",
        "text_secondary": "#cbd5e1",
    },
    "ocean": {
        "primary": "#0369a1",
        "secondary": "#0891b2",
        "success": "#0891b2",
        "dark_bg": "#020617",
        "dark_surface": "#1e293b",
        "text_primary": "#f9fafb",
        "text_secondary": "#cbd5e1",
    },
}

def get_theme_css(theme_name: str = "indigo_moderno"):
    """Genera CSS personalizado según tema elegido."""
    theme = THEMES.get(theme_name, THEMES["indigo_moderno"])
    css = f"""
    <style>
    :root {{
        --primary: {theme['primary']};
        --secondary: {theme['secondary']};
        --success: {theme['success']};
        --dark-bg: {theme['dark_bg']};
        --dark-surface: {theme['dark_surface']};
        --text-primary: {theme['text_primary']};
        --text-secondary: {theme['text_secondary']};
    }}
    /* ... resto de CSS ... */
    </style>
    """
    return css

# Usar:
st.markdown(get_theme_css("ocean"), unsafe_allow_html=True)
```

---

### **Método 3: Selector de Tema Interactivo**

```python
def render_theme_selector():
    """Permite al usuario cambiar el tema en vivo."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        theme = st.selectbox(
            "Elige tema:",
            ["indigo_moderno", "ciberfy", "ocean", "sunset", "forest", "minimal"],
            key="theme_selector"
        )
    
    # Guardar tema elegido en session state
    st.session_state["current_theme"] = theme
    
    # Inyectar CSS respectivo
    st.markdown(get_theme_css(theme), unsafe_allow_html=True)

# Llamar:
render_theme_selector()
```

---

## 🎨 Previsualizaciones en Consola

### **ÍNDIGO MODERNO (Default)**
```
Botón Primario:   #6366f1 (Índigo) → #8b5cf6 (Púrpura)
Botón Secundario: #ec4899 (Rosa)
Éxito:            #10b981 (Verde esmeralda)
Fondo:            #0f172a (Negro azulado)
Superficie:       #1e293b (Gris azul)
Texto:            #f9fafb (Blanco suave)
Sensación:        Profesional, moderno, tech
```

### **CIBERFY**
```
Botón Primario:   #d946ef (Magenta) → #c026d3 (Magenta oscuro)
Botón Secundario: #0891b2 (Cian)
Éxito:            #06b6d4 (Cyan claro)
Fondo:            #0a0a0a (Negro puro)
Superficie:       #18181b (Gris oscuro)
Texto:            #f9fafb (Blanco)
Sensación:        Futurista, energético, cyberpunk
```

### **OCEAN**
```
Botón Primario:   #0369a1 (Azul) → #0c4a6e (Azul profundo)
Botón Secundario: #0891b2 (Turquesa)
Éxito:            #0891b2 (Cyan)
Fondo:            #020617 (Negro oscuro)
Superficie:       #1e293b (Gris azul)
Texto:            #f9fafb (Blanco)
Sensación:        Confiable, profesional, fintech
```

### **SUNSET**
```
Botón Primario:   #ea580c (Naranja) → #f97316 (Naranja claro)
Botón Secundario: #d97706 (Ámbar naranja)
Éxito:            #65a30d (Verde lima)
Fondo:            #1c1917 (Marrón oscuro)
Superficie:       #292524 (Gris cálido)
Texto:            #f9fafb (Blanco)
Sensación:        Creativo, cálido, acogedor
```

### **FOREST**
```
Botón Primario:   #059669 (Verde) → #10b981 (Verde éxito)
Botón Secundario: #0369a1 (Azul)
Éxito:            #10b981 (Verde esmeralda)
Fondo:            #0c2e1f (Verde muy oscuro)
Superficie:       #1f3a34 (Verde gris)
Texto:            #f9fafb (Blanco)
Sensación:        Sostenible, natural, salud
```

### **MINIMAL**
```
Botón Primario:   #7c3aed (Púrpura) → #8b5cf6 (Púrpura claro)
Botón Secundario: #6b7280 (Gris neutral)
Éxito:            #8b5cf6 (Púrpura claro)
Fondo:            #18181b (Negro)
Superficie:       #27272a (Gris oscuro)
Texto:            #f9fafb (Blanco)
Sensación:        Minimalista, elegante, corporativo
```

---

## 🔍 Consideraciones al Cambiar Colores

### **Contraste (Accesibilidad WCAG)**
- ✅ Buen contraste: Índigo sobre negro (#6366f1 sobre #0f172a)
- ❌ Mal contraste: Rosa pálida sobre blanco (#fda4af sobre #fff)
- **Herramienta:** [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

### **Armonía de Colores**
- **Complementarios:** Índigo (#6366f1) + Naranja (#f97316)
- **Análogos:** Índigo (#6366f1) + Púrpura (#a78bfa)
- **Triádico:** Índigo + Naranja + Verde

### **Saturation & Brightness**
- Colores primarios: Más saturados (70-100%)
- Colores secundarios: Menos saturados (50-70%)
- Estados hover: 10-15% más claros/oscuros

---

## 🛠️ Herramientas Recomendadas

1. **[Coolors.co](https://coolors.co/)** - Generador de paletas armónicas
2. **[WebAIM](https://webaim.org/resources/contrastchecker/)** - Verificador de contraste
3. **[Polychrom](https://www.polychrom.io/)** - Paletas profesionales
4. **[Color Space](https://www.colorspace.io/)** - Paletas generadas con IA

---

## 💾 Guardar tu Paleta Personalizada

Crea un archivo `custom_theme.py`:

```python
# custom_theme.py

CUSTOM_THEME = {
    "name": "Mi Tema Personalizado",
    "primary": "#tu_color_primario",      # Tu índigo favorito
    "primary_dark": "#tu_color_oscuro",   # Versión oscura
    "secondary": "#tu_secundario",        # Tu rosa o diferente
    "success": "#tu_éxito",               # Verde o lo que prefieras
    "warning": "#tu_warning",             # Ámbar u otro
    "error": "#tu_error",                 # Rojo u otro
    "dark_bg": "#tu_fondo",              # Negro con tonalidad
    "dark_surface": "#tu_superficie",     # Gris con tonalidad
    "text_primary": "#tu_texto",         # Blanco puro o suave
    "text_secondary": "#tu_texto_gris",  # Gris suave
}

# Usar:
from custom_theme import CUSTOM_THEME
# Inyectar en CSS variables
```

---

## 📊 Tabla Rápida de Cambios

| Elemento | Paleta | Default | Ejemplo Alt. |
|----------|--------|---------|--------------|
| **Botón Principal** | Índigo | `#6366f1` | Ocean: `#0369a1` |
| **Botón Hover** | Púrpura | `#8b5cf6` | Ciberfy: `#c026d3` |
| **Secundario** | Rosa | `#ec4899` | Ocean: `#0891b2` |
| **Éxito** | Verde | `#10b981` | Forest: `#059669` |
| **Fondo** | Negro azul | `#0f172a` | Ciberfy: `#0a0a0a` |
| **Superficie** | Gris azul | `#1e293b` | Sunset: `#292524` |

---

## ✨ Combinaciones Ganadoras (Probadas)

1. **Profesional + Confianza:**  
   Primario: Índigo + Secundario: Azul marino

2. **Moderno + Energético:**  
   Primario: Magenta + Secundario: Cian

3. **Corporativo + Seguro:**  
   Primario: Azul océano + Secundario: Turquesa

4. **Creativo + Amigable:**  
   Primario: Naranja + Secundario: Lima

5. **Sostenible + Natural:**  
   Primario: Verde + Secundario: Azul

---

_¡Personaliza tu app con la paleta perfecta! 🎨_
