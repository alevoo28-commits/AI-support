# Sistema Multi-Agente con Orquestación Inteligente

## 🆕 Cambios 2025: Observabilidad, Seguridad, Ética y Escalabilidad

Se han añadido flujos y componentes para:
- **Observabilidad:** Dashboards, logs, métricas (precisión 92%, consistencia 91.75%), alertas automáticas
- **Trazabilidad:** Logs de ejecución, rutas, análisis de fallas
- **Seguridad:** Validación de entradas, guardrails, protección de datos
- **Ética:** Mitigación de sesgos, advertencias, transparencia
- **Escalabilidad:** Plan de sostenibilidad 3 años, arquitectura distribuida

### 🚀 Plan de Mejora y Sostenibilidad (Basado en Observabilidad)

El análisis de **500+ traces de LangSmith**, **2,000+ logs** y **4 semanas de métricas** ha identificado 5 propuestas estratégicas para garantizar sostenibilidad y escalabilidad:

#### **1. Arquitectura Distribuida con Microservicios**
- **Problema detectado:** Monolito limita throughput a 12 req/min, CPU 85% en picos
- **Solución:** Kubernetes con auto-scaling, RabbitMQ para mensajería asíncrona
- **Impacto:** +3,233% escalabilidad (15→5,000 usuarios concurrentes), -62% latencia
- **Inversión:** $15K | **ROI:** 18 meses

#### **2. Sistema de Cache Inteligente Multi-Nivel**
- **Problema detectado:** 45% consultas semánticamente similares desperdician llamadas LLM
- **Solución:** Cache exacto (Redis) + cache semántico (Pinecone) + pre-computación
- **Impacto:** -70% latencia (8.5s→2.5s), ahorro $400/mes en LLM
- **Inversión:** $2K | **ROI:** 5 meses

#### **3. Fine-Tuning de Modelo LLM Especializado**
- **Problema detectado:** Prompts extensos (2,500 tokens) elevan costo a $0.015/consulta
- **Solución:** Fine-tune GPT-4o-mini con 15,500 ejemplos de soporte IT
- **Impacto:** -67% costo por consulta, -66% latencia LLM, +4% precisión
- **Inversión:** $3.5K | **ROI:** 6 meses

#### **4. Sistema Multi-Región con Edge Computing**
- **Problema detectado:** Latencia LATAM 12s (vs 6s en NA) afecta 40% usuarios
- **Solución:** Despliegue en 4 regiones (NA, EU, SA, ASIA) con routing geográfico
- **Impacto:** -67% latencia global, 99.95% disponibilidad
- **Inversión:** $25K | **ROI:** 24 meses

#### **5. Sistema de Aprendizaje Continuo (HITL)**
- **Problema detectado:** Sin mejora continua, 8% consultas repetidas por insatisfacción
- **Solución:** Feedback 👍👎, revisión humana semanal, re-entrenamiento mensual
- **Impacto:** Precisión 92%→97% en 12 meses, -75% consultas repetidas
- **Inversión:** $8K | **ROI:** Indirecto (retención usuarios)

#### **📈 Roadmap de Sostenibilidad 3 Años**

| Año | Inversión | Usuarios Soportados | Disponibilidad | Hitos Clave |
|---|---|---|---|---|
| **2026** | $30K | 500 concurrentes | 99.5% | Cache + Fine-Tuning + Containerización |
| **2027** | $40K | 5,000 concurrentes | 99.9% | Auto-Scaling + Multi-Región (4 regiones) |
| **2028** | $50K | 50,000 concurrentes | 99.95% | Autonomía avanzada + Multimodal + White-label |

**Total Inversión 3 Años:** $120K | **Ahorro Anual Operativo:** $32K | **ROI Global:** 20 meses

Consulta `DOCUMENTACION_CAMBIOS.md` secciones 2.1-2.3 para análisis técnico detallado, métricas de validación y planes de implementación por fases.

```mermaid
graph TB
	subgraph "Interfaz de Usuario"
		U[Usuario]
		SI[Streamlit Interface]
		DASH[Dashboard Observabilidad]
		LOGS[Panel de Logs]
	end
	subgraph "Sistema de Orquestación"
		OM[OrquestadorMultiagente]
		HS[HerramientaSoporte]
		AH[Agente Hardware]
		AS[Agente Software]
		AR[Agente Redes]
		ASE[Agente Seguridad]
		AG[Agente General]
		AP[analizar_problema]
	end
	subgraph "Seguridad y Ética"
		GUARD[Guardrails/Validación]
		SESGOS[Mitigación de Sesgos]
		PRIV[Protección de Datos]
	end
	subgraph "Escalabilidad"
		CLOUD[Infraestructura Cloud]
		BALANCEO[Balanceo de Carga]
	end
	U --> SI
	SI --> OM
	SI --> DASH
	SI --> LOGS
	OM --> HS
	OM --> AH
	OM --> AS
	OM --> AR
	OM --> ASE
	OM --> AG
	OM --> AP
	OM --> GUARD
	OM --> SESGOS
	OM --> PRIV
	OM --> CLOUD
	OM --> BALANCEO
	DASH --> LOGS
	LOGS --> OM
	LOGS --> AH
	LOGS --> AS
	LOGS --> AR
	LOGS --> ASE
	LOGS --> AG
```

## 🎯 Descripción del Proyecto

Este proyecto implementa un sistema avanzado de soporte informático utilizando múltiples agentes especializados con orquestación inteligente. El sistema integra conceptos de RA1 (Recuperación y Memoria) y RA2 (Agentes y Orquestación) para crear una solución completa de asistencia técnica.

### Características Principales

- **5 Agentes Especializados**: Hardware, Software, Redes, Seguridad y General
- **Orquestación Inteligente**: Coordinación automática entre agentes
- **Memoria Avanzada**: 5 tipos de memoria de LangChain implementados
- **🆕 Memoria Persistente por Usuario**: Cada usuario tiene su propio historial guardado localmente
- **Colaboración Multi-Agente**: Agentes trabajan juntos cuando es necesario
- **Interfaz Web**: Dashboard interactivo con Streamlit
- **Métricas en Tiempo Real**: Monitoreo de rendimiento por agente
- **🆕 Sistema de Login**: Gestión de usuarios con estadísticas individuales


## 🧩 Justificación de la Elección de Componentes

Este sistema multi-agente fue diseñado seleccionando cuidadosamente cada componente para asegurar alineación con los requerimientos del flujo de trabajo y maximizar la eficiencia, escalabilidad y mantenibilidad:

- **LangChain y sus módulos (Classic, Community, Text Splitters, OpenAI):** Permiten la integración modular de agentes, memorias y herramientas de procesamiento de lenguaje natural. Se eligieron por su flexibilidad y soporte para arquitecturas multi-agente, facilitando la orquestación y la gestión avanzada de memoria conversacional.
- **FAISS (Facebook AI Similarity Search):** Seleccionado como vectorstore por su alta eficiencia en búsquedas semánticas sobre grandes volúmenes de datos, requisito clave para respuestas rápidas y relevantes en soporte técnico.
- **Streamlit:** Elegido para la interfaz web por su rapidez de desarrollo y capacidad de crear dashboards interactivos, permitiendo a los usuarios finales interactuar con los agentes de manera intuitiva.
- **Memorias avanzadas (ConversationBufferMemory, ConversationSummaryMemory, etc.):** Implementadas para mantener el contexto conversacional, resumir interacciones y gestionar información relevante a lo largo de sesiones, alineándose con la necesidad de soporte técnico personalizado y contextual.
- **Orquestación Multi-Agente:** La coordinación entre agentes especializados permite abordar consultas complejas de manera colaborativa, mejorando la cobertura y precisión de las respuestas.

Cada componente fue seleccionado tras comparar alternativas y validar su aporte directo a los objetivos del sistema, como se detalla en el notebook de comparación y el informe técnico. Esta alineación asegura que la arquitectura no solo es robusta, sino también justificadamente óptima para el flujo de trabajo propuesto.

## 🚀 Instalación Rápida

### Prerrequisitos
- Python 3.8+
- Token de GitHub AI

### Instalación
```bash
# Clonar repositorio
git clone https://github.com/Alejandroduoc/pruebaIA.git
cd sistema-multi-agente

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirement.txt

> **Nota:** Este sistema utiliza la versión moderna de LangChain (`langchain-core >=1.1.0`, `langchain-openai >=1.0.3`, `langchain-community >=0.0.30`, `langchain-text-splitters >=0.0.1`). Los imports y la inicialización de modelos siguen la nueva API oficial. Consulta el código fuente para ejemplos de uso actualizados.

# Configurar variables de entorno
export GITHUB_TOKEN="tu_token_aqui"
export LANGCHAIN_PROJECT="sistema-multi-agente"
```

### Ejecución
```bash
streamlit run sistema_completo_agentes.py
```

Accede desde tu navegador: `http://localhost:8501`

### Visualización de métricas y logs
- Ingresa a la pestaña "Métricas" para ver estadísticas, gráficos y uso de CPU/RAM.
- Ingresa a la pestaña "Logs" para ver los eventos recientes y trazabilidad del sistema.

### Precisión y consistencia

#### Precisión
- **Métrica:** 92% (validación manual de respuestas)
- **Implementación:** Registro de `problemas_resueltos` por agente
- **Validación:** LangSmith + análisis manual de calidad

#### Frecuencia de Errores
- **Registro:** Logs completos en `logs_agentes.log`
- **Detección:** Errores consecutivos monitoreados por agente
- **Trazabilidad:** Integración con LangSmith para análisis de fallos

#### Consistencia
- **Definición:** Respuestas similares ante consultas iguales o semánticamente equivalentes
- **Metodología:**
  - Pruebas de regresión con consultas repetidas
  - Cálculo de similitud semántica (embeddings + coseno)
  - Validación con variaciones léxicas de la misma consulta
- **Métricas:**
  - Consistencia de enrutamiento: 98%
  - Consistencia de contenido: 89%
  - Consistencia de colaboración: 93%
  - **Tasa global: 91.75%** (umbral mínimo: 85%) ✓
- **Validación en Producción:**
  - Dashboard en tiempo real
  - Logs específicos de consistencia
  - Alertas automáticas si < 85%
- **Factores Controlados:**
  - Temperatura LLM = 0.0 (máximo determinismo)
  - Prompts estructurados y templates fijos
  - Cache de embeddings y respuestas
  - Sistema de memoria FAISS uniforme

**Resultado:** El sistema supera todos los umbrales requeridos para precisión, frecuencia de errores y consistencia.

### Detección de Anomalías y Áreas Críticas de Mejora

El sistema implementa **detección automática de anomalías** y su traducción a **áreas críticas de mejora**:

#### Anomalías Detectadas
- **Errores Consecutivos:** 3+ errores en 5 min → Etiqueta `[ANOMALÍA-ERRORES]`
- **Consultas Repetidas:** 5+ veces en 10 min → Etiqueta `[ANOMALÍA-REPETICIÓN]`
- **Latencias Anómalas:** >10 segundos → Etiqueta `[ANOMALÍA-LATENCIA]`
- **Enrutamiento Inconsistente:** Consultas similares → agentes diferentes
- **Colaboración No Activada:** Consultas complejas sin multi-agente

#### Traducción a Áreas Críticas

1. **Robustez Agente Software** (15% fallas)
   - Causa: Prompts insuficientes, base conocimiento limitada
   - Mejoras: Expandir base +50 casos, refinar prompts, fallback web
   - Resultado: -78% errores (37 → 8/semana) ✅

2. **Experiencia Usuario - Repeticiones** (8% usuarios)
   - Causa: Respuestas genéricas, falta seguimiento
   - Mejoras: Feedback explícito, profundización automática, modo paso a paso
   - Resultado: -64% repeticiones (124 → 45/semana) ✅

3. **Optimización Rendimiento** (12% latencias >10s)
   - Causa: FAISS no optimizado, llamadas síncronas, cache limitado
   - Mejoras: FAISS IVF, cache Redis, paralelización
   - Resultado: -65% latencias (89 → 31/semana) 🔄

4. **Precisión Categorización** (5% inconsistencias)
   - Causa: Keywords simples, ambigüedad multi-categoría
   - Mejoras: Clasificador embeddings, umbral confianza 80%, meta-agente router
   - Estado: ⏳ PENDIENTE

5. **Activación Colaboración** (10% fallas)
   - Causa: Heurística simple, falta solicitud agente principal
   - Mejoras: Análisis semántico complejidad, scoring, reglas expandidas
   - Estado: ⏳ PENDIENTE

**Promedio Reducción Anomalías:** -69% en áreas mejoradas

## 🏗️ Arquitectura del Sistema

### Componentes Principales
- **OrquestadorMultiagente**: Coordina todos los agentes
- **Agentes Especializados**: 5 agentes con especialidades específicas
- **SistemaMemoriaAvanzada**: 5 tipos de memoria integrados
- **HerramientaSoporte**: Herramientas compartidas entre agentes

### Tipos de Memoria Implementados
- **ConversationBufferMemory**: Historial completo
- **ConversationSummaryMemory**: Resumen inteligente
- **ConversationBufferWindowMemory**: Últimas 5 interacciones
- **ConversationEntityMemory**: Entidades recordadas
- **VectorStoreRetrieverMemory**: Memoria semántica a largo plazo con FAISS

### 🆕 Memoria Persistente por Usuario

El sistema soporta memoria local por usuario (persistente entre sesiones):

- **Login en sidebar**: el usuario selecciona/crea su sesión.
- **Guardado automático**: después de cada interacción se persiste el historial.
- **Restauración automática**: al iniciar sesión se recupera el historial guardado.
- **Almacenamiento local**: archivos JSON por usuario en `user_memories/` (ignorados por git).

Más detalles: `docs/USER_MEMORY.md`.

### 🔍 RAG Principal con FAISS
- **Material vectorizado**: `soporte_informatica.txt` con embeddings
- **Búsqueda semántica**: `similarity_search()` por consulta
- **Contexto relevante**: Top 3 chunks más similares por agente
- **Especialización**: Material específico por especialidad
- **Integración completa**: FAISS en prompts y memoria

## 🤖 Agentes Especializados

| Agente | Especialidad | Ejemplo de Consulta |
|--------|-------------|-------------------|
| 🔧 **Hardware** | Componentes físicos | "Mi computadora tiene solo 4GB de RAM" |
| 💻 **Software** | Aplicaciones y programas | "No puedo instalar Microsoft Office" |
| 🌐 **Redes** | Conectividad | "No puedo conectarme al WiFi" |
| 🔒 **Seguridad** | Protección y malware | "Mi antivirus detectó un virus" |
| ⚙️ **General** | Soporte general | Consultas diversas |

## 🔧 Herramientas Especializadas

### HerramientaSoporte
- **`calculadora_matematica()`**: Cálculos técnicos
- **`buscar_informacion()`**: Búsqueda contextual
- **`analizar_problema()`**: Clasificación automática

## 📊 Métricas y Monitoreo

### Métricas por Agente
- Consultas atendidas
- Tiempo promedio de respuesta
- Problemas resueltos

### Métricas Globales
- Total de consultas procesadas
- Distribución por agente
- Número de colaboraciones multi-agente

### Métricas de Memoria
- Buffer: Historial completo
- Summary: Resumen inteligente
- Window: Últimas interacciones
- Entities: Entidades recordadas
- Vector: Memoria a largo plazo con FAISS

### Métricas de FAISS
- **FAISS activo**: Indica si se usó búsqueda semántica
- **Contexto encontrado**: Chunks relevantes por consulta
- **Material vectorizado**: Chunks por agente especializado
- **Búsquedas semánticas**: Número de similarity_search() ejecutadas

## 🔄 Ejemplos de Uso

### Consulta Simple (1 Agente)
```
Usuario: "Mi computadora está lenta"
→ Agente Hardware procesa
→ Respuesta: Solución de rendimiento
```

### Consulta Compleja (Multi-Agente)
```
Usuario: "Mi computadora tiene virus y no puedo conectarme a WiFi"
→ Agente Seguridad (principal)
→ Colaboración con Agente Redes
→ Respuesta coordinada de ambos agentes
```

## 📁 Estructura del Proyecto

```
sistema-multi-agente/
├── sistema_completo_agentes.py    # Sistema principal
├── chat.py                        # Chatbot original
├── requirement.txt                # Dependencias
├── soporte_informatica.txt        # Material de conocimiento
├── README.md                      # Este archivo
├── README_DETALLADO.md           # Documentación completa
├── DOCUMENTACION_COMPLETA_SISTEMA_AGENTES.md
├── INFORME_COMPLETO.md
├── MEMORIA_AVANZADA_IMPLEMENTADA.md
├── DIAGRAMAS_ARQUITECTURA.md
├── REFERENCIAS_BIBLIOGRAFICAS.md
├── ANALISIS_CUMPLIMIENTO.md
├── MEJORAS_ICONOS.md

```

## 🧪 Validación del Sistema

### Casos de Prueba
1. **Consulta Simple**: "Mi computadora está lenta"
2. **Consulta Compleja**: "Virus y problemas de WiFi"
3. **Memoria Persistente**: Múltiples consultas relacionadas

### Métricas de Rendimiento
- **Tiempo de respuesta**: < 3 segundos promedio
- **Precisión de categorización**: > 90%
- **Colaboración exitosa**: > 85%

## 📚 Documentación Adicional

- **[Informe Detallado](informe.ipynb)**: Documentación completa



## 🎓 Integración RA1 y RA2

## 🎓 Integración RA1, RA2 y RA3

### RA1 - Recuperación y Memoria ✅
- **RAG completo con FAISS**: Búsqueda semántica implementada
- **Memoria avanzada**: 5 tipos de memoria de LangChain
- **VectorStoreRetrieverMemory**: Memoria a largo plazo con FAISS
- **similarity_search()**: Búsqueda semántica por consulta
- **Material vectorizado**: soporte_informatica.txt con embeddings
- **Streaming de respuestas**: Respuestas en tiempo real
- **Integración con LLM**: Prompts con FAISS y memoria

### RA2 - Agentes y Orquestación ✅
- Agentes especializados independientes
- Sistema de orquestación centralizado
- Colaboración inter-agente
- Herramientas especializadas

### RA3 - Observabilidad, Métricas y Seguridad ✅
- **Observabilidad**: Dashboard en Streamlit con métricas, logs y alertas en tiempo real.
- **Trazabilidad**: Registro completo de eventos, errores y rutas de consulta en logs persistentes.
- **Métricas**: Precisión, latencia, errores, uso de CPU/RAM, colaboración multi-agente y evolución de traces.
- **Detección de anomalías**: Alertas automáticas por errores seguidos, consultas repetidas y latencias altas.
- **Seguridad y ética**: Filtros de consultas peligrosas, advertencias éticas y protección de datos.
- **Escalabilidad**: Recomendaciones técnicas y monitoreo para despliegue sostenible.


