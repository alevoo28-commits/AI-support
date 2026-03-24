# 🎨 Visual Reference Guide - Previsualización de Componentes

## 📸 Estructura General de la App

### **Layout Responsivo**
```
DESKTOP (1920x1080)
┌─────────────────────────────────────────────────────────────────────┐
│ 🤖 AI Support                                          👤 user@fcfm │
│ Sistema Multiagente FCFM - Login: 2:34 PM                          │
├──────────────────┬────────────────────────────────────────────────────┤
│                  │                                                     │
│  SIDEBAR         │           MAIN CONTENT                            │
│  (colapsable)    │           (responsive grid)                       │
│                  │                                                     │
│  🎯 Navegación   │  💬 Chat, Agentes, KB, Config, Diags             │
│  ──────────────  │  ────────────────────────────────────────          │
│  • 💬 Chat       │                                                     │
│  • 🤖 Agentes    │  ┌──────────────────────────────────────────────┐ │
│  • 📚 KB         │  │                                                │ │
│  • ⚙️ Config     │  │  Contenido según sección activa               │ │
│  • 📊 Diags      │  │                                                │ │
│                  │  │  - Cards tipo bento                            │ │
│  ⚡ Herramientas │  │  - Chat bubbles                                │ │
│  [📊] [🗑️]      │  │  - Formularios                                 │ │
│                  │  │  - Gráficos                                    │ │
│  [🚪 Logout]     │  │                                                │ │
│                  │  └──────────────────────────────────────────────┘ │
│                  │  ┌──────────────────────────────────────────────┐ │
│                  │  │ [Escribe mensaje...]                 [send] │ │
│                  │  └──────────────────────────────────────────────┘ │
└──────────────────┴────────────────────────────────────────────────────┘

MOBILE (375x667)
┌──────────────────┐
│ ☰ AI Support     │
│ user@fcfm        │
├──────────────────┤
│                  │
│ Sidebar colapse  │
│ Content full     │
│ width            │
│                  │
│ Cards 1 column   │
│ Chat bubbles     │
│ Input bottom     │
│                  │
│ [Escribe...]     │
│                  │
└──────────────────┘
```

---

## 🎨 Paleta de Colores Actual

### **Índigo Moderno (Default)**

**Primarios:**
```
┌─────────────────────────────┐
│ Primario:  #6366f1          │  ← Botones principales
│ Oscuro:    #4f46e5          │  ← Hover, enfasis
│ Secundario: #ec4899         │  ← Acentos
└─────────────────────────────┘
```

**Backgrounds:**
```
┌─────────────────────────────┐
│ Fondo:     #0f172a          │  ← Fondo principal (black-blue)
│ Superficie: #1e293b         │  ← Cards, containers
│ Hover:     #293548          │  ← Hover surface
└─────────────────────────────┘
```

**Texto:**
```
┌─────────────────────────────┐
│ Primario:   #f9fafb         │  ← Texto principal (blanco suave)
│ Secundario: #cbd5e1         │  ← Texto suave, captions
│ Terciario:  #94a3b8         │  ← Placeholder, disabled
└─────────────────────────────┘
```

**Estados:**
```
┌─────────────────────────────┐
│ ✅ Éxito:   #10b981         │  ← Verde esmeralda
│ ⚠️ Warning: #f59e0b         │  ← Ámbar
│ ❌ Error:    #ef4444         │  ← Rojo
│ ℹ️ Info:     #6366f1         │  ← Índigo
└─────────────────────────────┘
```

### **Gradientes Utilizados**

```css
/* Primario → Secundario */
background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
/* Resultado: Índigo → Púrpura (botones, headers) */

/* Dark Surface */
background: linear-gradient(180deg, rgba(30,41,59,0.6) 0%, rgba(15,23,41,0.8) 100%);
/* Resultado: Gris azul translúcido + blur */

/* Éxito */
background: linear-gradient(135deg, #10b981 0%, #059669 100%);
/* Resultado: Verde claro → Verde profundo */
```

---

## 🧩 Componentes Principales

### **1. HEADER ANIMADO**

```python
st.markdown("""
<div style="animation: fadeInDown 0.6s ease-out;">
    <h1 style="
        background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    ">🤖 AI Support</h1>
    <p style="color: #a0aec0; margin: 0.5rem 0 0 0;">
        Sistema Multiagente de Soporte Informático FCFM
    </p>
</div>
""", unsafe_allow_html=True)

# Resultado visual:
# ───────────────────────────────────
# 🤖 AI Support                    ← Gradiente índigo→rosa, animado
# Sistema Multiagente FCFM         ← Gris suave
# ───────────────────────────────────
```

---

### **2. BENTO CARD (Tarjeta Moderna)**

```python
st.markdown("""
<div class="bento-card scale-in">
    <div class="bento-card-header">
        <div class="bento-card-icon">🖨️</div>
        <h4 class="bento-card-title">Impresoras Conectadas</h4>
        <span class="badge">12 disponibles</span>
    </div>
    <p style="margin: 0; color: #cbd5e1; line-height: 1.5;">
        Sistema de diagnóstico automático para impresoras de red FCFM.
        Soporta modelos MP, HPL, Canon y Xerox.
    </p>
</div>
""", unsafe_allow_html=True)

# Resultado visual:
# ┌─────────────────────────────────────────┐
# │ 🖨️  Impresoras Conectadas  [12 DISP]   │  ← Icon, title, badge
# │                                          │
# │ Sistema de diagnóstico automático...    │  ← Descripción
# │ Soporta modelos MP, HPL, Canon...       │
# └─────────────────────────────────────────┘ ← Glass bg, hover lift
```

---

### **3. CHAT BUBBLES (Differenciadas)**

```python
# Usuario (Derecha, Índigo)
st.markdown("""
<div style="display: flex; justify-content: flex-end; margin: 0.5rem 0;">
    <div style="
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        padding: 1rem 1.25rem;
        border-radius: 16px 16px 4px 16px;
        max-width: 75%;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
        animation: slideInRight 0.3s ease-out;
    ">
        Hola, ¿cómo puedo resetear mi contraseña?
    </div>
</div>
""", unsafe_allow_html=True)

# Agente (Izquierda, Glasmorphism)
st.markdown("""
<div style="display: flex; justify-content: flex-start; margin: 0.5rem 0;">
    <div style="
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #f9fafb;
        padding: 1rem 1.25rem;
        border-radius: 16px 16px 16px 4px;
        max-width: 75%;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        animation: slideInLeft 0.3s ease-out;
    ">
        Puedes resetear tu contraseña en https://soporte.fcfm.cl/reseteo
    </div>
</div>
""", unsafe_allow_html=True)

# Resultado visual:
#                                    ┌──────────────────────────────┐
#                                    │ Tú: ¿Cómo reseteo pwd?       │
#                                    └──────────────────────────────┘
#                                       14:32
#
# ┌──────────────────────────────────┐
# │ 🤖: Ve a https://soporte.fcfm... │
# └──────────────────────────────────┘
#    14:33
```

---

### **4. BOTÓN PRIMARIO (Gradiente + Sombra)**

```python
st.button(
    "✅ Enviar Mensaje",
    use_container_width=True,
    type="primary"
)

# CSS resultante:
# background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
# box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
# transform en hover: translateY(-2px);

# Resultado visual:
# ┌─────────────────────────┐
# │ ✅ Enviar Mensaje       │  ← Gradiente índigo→púrpura
# └─────────────────────────┘     Sombra suave
#      hover: levantado 2px
```

---

### **5. INPUT GLASMORPHISM**

```python
st.text_input("Escribe tu consulta aquí...")

# CSS:
# background: rgba(30, 41, 59, 0.5);  ← Semi-transparente
# backdrop-filter: blur(10px);         ← Blur suave
# border: 1px solid rgba(99, 102, 241, 0.2);  ← Border índigo suave
# Focus: box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);

# Resultado visual (normal):
# ┌─────────────────────────────────────────────┐
# │ [Escribe tu consulta aquí...               │  ← Fondo translúcido
# └─────────────────────────────────────────────┘

# Resultado visual (focus):
# ┌─────────────────────────────────────────────┐  ← Border índigo
# │ [█ Escribiendo...                           │  ← Halo glow
# └─────────────────────────────────────────────┘
```

---

### **6. ALERTAS COLOREADAS**

```python
# Success
st.success("✅ Conexión establecida con el servidor")
# ┌─────────────────────────────────────────────┐
# │ ✅ Conexión establecida...                 │  ← Fondo verde/15%
# └─────────────────────────────────────────────┘     Border verde

# Warning
st.warning("⚠️ Verificación de seguridad requerida")
# ┌─────────────────────────────────────────────┐
# │ ⚠️ Verificación de seguridad...             │  ← Fondo ámbar/15%
# └─────────────────────────────────────────────┘     Border ámbar

# Error
st.error("❌ Error: Token expirado")
# ┌─────────────────────────────────────────────┐
# │ ❌ Error: Token expirado                    │  ← Fondo rojo/15%
# └─────────────────────────────────────────────┘     Border rojo

# Info
st.info("ℹ️ Este es un mensaje informativo")
# ┌─────────────────────────────────────────────┐
# │ ℹ️ Este es un mensaje informativo           │  ← Fondo índigo/15%
# └─────────────────────────────────────────────┘     Border índigo
```

---

### **7. MÉTRICAS (Stats Cards)**

```python
st.metric(
    label="Mensajes Procesados",
    value="1,234",
    delta="↑ 12 hoy"
)

# Resultado visual:
# ┌──────────────────────────────────┐
# │ Mensajes Procesados              │  ← Label gris
# │ 1,234                            │  ← Valor índigo, grande
# │ ↑ 12 hoy                         │  ← Delta, verde
# └──────────────────────────────────┘     Background glass
```

---

### **8. SIDEBAR HEADER (Glasmorphism)**

```python
st.markdown("""
<div class="sidebar-header">
    <h2>🎯 Navegación</h2>
</div>
""", unsafe_allow_html=True)

# Resultado visual:
# ┌─────────────────────┐
# │ 🎯 Navegación       │  ← Gradiente índigo→rosa
# └─────────────────────┘     Redondeado 16px
#                             Box-shadow suave
#                             Animación fade-in
```

---

### **9. LOADING SPINNER (Personalizado)**

```python
st.markdown("""
<div style="display: flex; align-items: center; gap: 1rem; padding: 2rem;">
    <div style="
        width: 30px;
        height: 30px;
        border: 3px solid rgba(99, 102, 241, 0.2);
        border-top: 3px solid #6366f1;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    "></div>
    <span>El agente está procesando tu consulta...</span>
</div>
""", unsafe_allow_html=True)

# Resultado visual:
# ◴ El agente está procesando tu consulta...
#   (spinner girando, border superior índigo)
```

---

### **10. TAB MODERNO**

```python
tabs = st.tabs(["💬 Chat", "📚 FAQ", "⚙️ Config"])

with tabs[0]:
    st.write("Contenido Chat")

# Resultado visual:
# [💬 Chat] 📚 FAQ   ⚙️ Config
# ════════════════════════════════
#
# Contenido Chat...
#
# (Tab activo: border-bottom índigo, texto blanco)
```

---

## 📊 Estructura de Código Típica

### **Patrón de Sección**

```python
def render_seccion_ejemplo():
    """Renderiza una sección de la app."""
    # 1. Título con animación
    st.markdown("""
    <div style="animation: fadeIn 0.5s ease-out;">
        <h2>📋 Título de Sección</h2>
        <p style="color: #cbd5e1;">Subtítulo descriptivo</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")  # Divider
    
    # 2. Grid de Cards (Bento)
    col1, col2, col3 = st.columns(3)
    with col1:
        render_bento_card("🔹", "Card 1", "Descripción...")
    with col2:
        render_bento_card("🔹", "Card 2", "Descripción...")
    with col3:
        render_bento_card("🔹", "Card 3", "Descripción...")
    
    st.markdown("---")
    
    # 3. Contenido principal
    tab1, tab2, tab3 = st.tabs(["Tab 1", "Tab 2", "Tab 3"])
    with tab1:
        st.write("Contenido Tab 1")
        # ... más elementos

# Llamar en main():
render_seccion_ejemplo()
```

---

## 🎬 Animaciones en Acción

### **1. Fade-In (0.5s)**
```css
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
/* Headers, cards, contenido al cargar */
```

### **2. Slide-In-Right (0.3s)**
```css
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
}
/* Chat bubbles usuario (derecha) */
```

### **3. Slide-In-Left (0.3s)**
```css
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}
/* Chat bubbles agente (izquierda) */
```

### **4. Scale-In (0.5s)**
```css
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
}
/* Carta que aparecen */
```

### **5. Pulse (2s infinito)**
```css
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
/* Indicadores de estado */
```

### **6. Spin (1s infinito)**
```css
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* Spinner de carga */
```

---

## 🌈 Casos de Uso de Color

### **Cuándo Usar Cada Color**

```
PRIMARY (#6366f1) → Botones principales, links, headers
SECONDARY (#ec4899) → Acentos, gradientes, énfasis
SUCCESS (#10b981) → Confirmaciones, estados OK
WARNING (#f59e0b) → Alertas, atención requerida
ERROR (#ef4444) → Errores, problemas
INFO (#6366f1) → Información informativa
DARK-BG (#0f172a) → Fondo principal
DARK-SURFACE (#1e293b) → Cards, containers
TEXT-PRIMARY (#f9fafb) → Texto principal
TEXT-SECONDARY (#cbd5e1) → Texto secundario, captions
```

---

## 📱 Responsive Breakpoints

```css
/* Desktop: 1920x1080 (default) */
/* Full layout con 3 columnas */

/* Tablet: 768x1024 */
@media (max-width: 1024px) {
    /* 2 columnas, sidebar colapsable */
}

/* Mobile: 375x667 */
@media (max-width: 768px) {
    /* 1 columna, sidebar hidden, full width */
    .bento-card { padding: 1rem; }
    .chat-bubble { max-width: 100%; }
}
```

---

## ✨ Efecto Glassmorphism

### **Composición Visual**

```
┌─────────────────────────────────┐
│  Fondo lejano (blurred)         │
│  (dark gradient #0f172a)         │
│                                  │
│  ┌───────────────────────────┐   │
│  │ Layer: rgba(30,41,59,0.5) │   │ ← Semi-transparente
│  │ Blur: 10px                │   │ ← Blur suave
│  │ Border: 1px transparent   │   │ ← Sutil edge
│  │ Shadow: 0 4px 16px        │   │ ← Profundidad
│  │                           │   │
│  │ Contenido visibles        │   │
│  │                           │   │
│  └───────────────────────────┘   │
│                                  │
└─────────────────────────────────┘

Resultado: Sensación de profundidad + modernidad
```

---

_Este documento es una referencia visual. Para más detalles técnicos, ver MODERN_UI_CHANGELOG.md_
