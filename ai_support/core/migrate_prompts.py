#!/usr/bin/env python3
"""
Script de migración: prompts.py → prompts_mysql.py

Ejecutar UNA VEZ después de habilitar MySQL:
    python -m ai_support.core.migrate_prompts
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def verificar_mysql():
    """Verifica que MySQL esté habilitado y configurado."""
    if os.getenv("AI_SUPPORT_MYSQL_ENABLE", "false").lower() != "true":
        logger.error("❌ MySQL no habilitado. Ver: AI_SUPPORT_MYSQL_ENABLE")
        return False
    
    requeridas = [
        "AI_SUPPORT_MYSQL_HOST",
        "AI_SUPPORT_MYSQL_USER",
        "AI_SUPPORT_MYSQL_PASSWORD",
        "AI_SUPPORT_MYSQL_DATABASE"
    ]
    
    for var in requeridas:
        if not os.getenv(var):
            logger.error(f"❌ Falta variable de entorno: {var}")
            return False
    
    logger.info("✅ MySQL configurado correctamente")
    return True


def migrar_prompts():
    """Ejecuta migración de prompts a MySQL."""
    from ai_support.core.prompts_mysql import inicializar_gestor
    
    try:
        logger.info("🔄 Inicializando GestorPromptsMySQL...")
        gestor = inicializar_gestor()
        
        if not gestor.conexion:
            logger.error("❌ No se pudo conectar a MySQL")
            return False
        
        logger.info("📋 Listando prompts en MySQL...")
        prompts = gestor.listar(solo_activos=False)
        
        logger.info(f"✅ Migración completada: {len(prompts)} prompts en MySQL")
        
        # Mostrar estado
        for nombre, info in list(prompts.items())[:5]:
            logger.info(f"   - {nombre}: v{info['version']}")
        
        if len(prompts) > 5:
            logger.info(f"   ... y {len(prompts) - 5} más")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante migración: {e}")
        return False


def mostrar_proximos_pasos():
    """Muestra instrucciones para completar migración."""
    logger.info("""
═══════════════════════════════════════════════════════════════
✅ MIGRACIÓN COMPLETADA
═══════════════════════════════════════════════════════════════

Próximos pasos:

1. 📝 Verificar prompts en MySQL:
   python -c "from ai_support.core.prompts_mysql import listar_prompts; 
              print(listar_prompts())"

2. 🔄 Actualizar código para usar nuevo gestor:
   - specialized_agent.py
   - multi_orchestrator.py
   - Otros archivos que usen prompts

3. 🧪 Ejecutar tests:
   python -m pytest tests/test_prompts_mysql.py

4. 🚀 Desplegar:
   git add -A
   git commit -m "Migración: prompts externalizados en MySQL"
   git push

═══════════════════════════════════════════════════════════════
    """)


def main():
    """Ejecuta migración."""
    logger.info("""
╔═══════════════════════════════════════════════════════════════╗
║  MIGRACIÓN: PROMPTS EXTERNALIZADOS EN MYSQL                  ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar
    if not verificar_mysql():
        logger.error("⚠️  Verificación fallida. Abortar.")
        return 1
    
    # Migrar
    if not migrar_prompts():
        logger.error("⚠️  Migración fallida. Abortar.")
        return 1
    
    # Mostrar próximos pasos
    mostrar_proximos_pasos()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
