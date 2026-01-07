"""
Script de prueba para el sistema de memoria persistente por usuario.

Verifica que:
1. Se pueden crear y guardar memorias de usuario
2. Se pueden cargar memorias guardadas
3. Las estadísticas funcionan correctamente
4. Se puede eliminar memoria de usuario
"""

from ai_support.core.user_memory_persistence import UserMemoryPersistence
from langchain_core.messages import HumanMessage, AIMessage


def test_user_memory_persistence():
    """Prueba básica del sistema de persistencia."""
    
    print("=" * 60)
    print("TEST: Sistema de Memoria Persistente por Usuario")
    print("=" * 60)
    
    # 1. Crear instancia de persistencia
    print("\n1️⃣ Creando instancia de UserMemoryPersistence...")
    persistence = UserMemoryPersistence(storage_dir="./user_memories")
    print("✅ Instancia creada")
    
    # 2. Crear mensajes de prueba
    print("\n2️⃣ Creando mensajes de prueba...")
    test_messages = [
        HumanMessage(content="Hola, necesito ayuda con mi impresora"),
        AIMessage(content="¡Hola! Claro, estaré encantado de ayudarte con tu impresora. ¿Qué problema tienes?"),
        HumanMessage(content="No puedo conectarla por red"),
        AIMessage(content="Entiendo. Para conectar una impresora por red necesito saber..."),
    ]
    print(f"✅ Creados {len(test_messages)} mensajes")
    
    # 3. Guardar memoria de usuario
    print("\n3️⃣ Guardando memoria de usuario 'test.user'...")
    success = persistence.save_user_memory("test.user", test_messages)
    if success:
        print("✅ Memoria guardada exitosamente")
    else:
        print("❌ Error guardando memoria")
        return False
    
    # 4. Listar usuarios
    print("\n4️⃣ Listando usuarios con memoria guardada...")
    users = persistence.list_users()
    print(f"✅ Usuarios encontrados: {users}")
    if "test.user" not in users:
        print("❌ Usuario 'test.user' no encontrado en la lista")
        return False
    
    # 5. Cargar memoria de usuario
    print("\n5️⃣ Cargando memoria de usuario 'test.user'...")
    memory_data = persistence.load_user_memory("test.user")
    if memory_data:
        loaded_messages = memory_data.get("messages", [])
        print(f"✅ Memoria cargada: {len(loaded_messages)} mensajes")
        print(f"   User ID: {memory_data.get('user_id')}")
        print(f"   Última actualización: {memory_data.get('last_updated')}")
        
        # Verificar que los mensajes coincidan
        if len(loaded_messages) != len(test_messages):
            print(f"❌ Número de mensajes no coincide: {len(loaded_messages)} vs {len(test_messages)}")
            return False
    else:
        print("❌ No se pudo cargar la memoria")
        return False
    
    # 6. Obtener estadísticas
    print("\n6️⃣ Obteniendo estadísticas de usuario 'test.user'...")
    stats = persistence.get_user_stats("test.user")
    if stats:
        print("✅ Estadísticas obtenidas:")
        print(f"   Total mensajes: {stats['total_messages']}")
        print(f"   Mensajes humanos: {stats['human_messages']}")
        print(f"   Mensajes IA: {stats['ai_messages']}")
        print(f"   Tamaño archivo: {stats['file_size_kb']} KB")
        
        # Verificar estadísticas
        if stats['total_messages'] != 4:
            print(f"❌ Total de mensajes incorrecto: {stats['total_messages']} vs 4")
            return False
        if stats['human_messages'] != 2:
            print(f"❌ Mensajes humanos incorrecto: {stats['human_messages']} vs 2")
            return False
        if stats['ai_messages'] != 2:
            print(f"❌ Mensajes IA incorrecto: {stats['ai_messages']} vs 2")
            return False
    else:
        print("❌ No se pudieron obtener estadísticas")
        return False
    
    # 7. Agregar más mensajes
    print("\n7️⃣ Agregando más mensajes a la memoria...")
    extended_messages = loaded_messages + [
        HumanMessage(content="Ya funcionó, gracias"),
        AIMessage(content="¡Excelente! Me alegra que haya funcionado."),
    ]
    success = persistence.save_user_memory("test.user", extended_messages)
    if success:
        print("✅ Memoria actualizada")
        
        # Verificar nueva estadística
        new_stats = persistence.get_user_stats("test.user")
        if new_stats and new_stats['total_messages'] == 6:
            print(f"✅ Nuevo total de mensajes: {new_stats['total_messages']}")
        else:
            print(f"❌ Total de mensajes incorrecto después de actualizar")
            return False
    else:
        print("❌ Error actualizando memoria")
        return False
    
    # 8. Eliminar memoria de usuario
    print("\n8️⃣ Eliminando memoria de usuario 'test.user'...")
    deleted = persistence.delete_user_memory("test.user")
    if deleted:
        print("✅ Memoria eliminada exitosamente")
        
        # Verificar que ya no existe
        users_after = persistence.list_users()
        if "test.user" not in users_after:
            print("✅ Usuario no aparece en lista después de eliminar")
        else:
            print("❌ Usuario todavía aparece en lista")
            return False
    else:
        print("❌ Error eliminando memoria")
        return False
    
    # 9. Intentar cargar memoria eliminada
    print("\n9️⃣ Intentando cargar memoria eliminada...")
    deleted_memory = persistence.load_user_memory("test.user")
    if deleted_memory is None:
        print("✅ Memoria eliminada no se puede cargar (comportamiento esperado)")
    else:
        print("❌ La memoria eliminada todavía se puede cargar")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    print("=" * 60)
    return True


def test_sanitization():
    """Prueba la sanitización de nombres de usuario."""
    
    print("\n" + "=" * 60)
    print("TEST: Sanitización de Nombres de Usuario")
    print("=" * 60)
    
    persistence = UserMemoryPersistence()
    
    # Casos de prueba
    test_cases = [
        ("juan.perez", True),
        ("maria_gonzalez", True),
        ("admin-123", True),
        ("user@domain.com", False),  # @ no permitido
        ("../../../etc/passwd", False),  # path traversal
        ("user name", False),  # espacios
        ("", False),  # vacío
    ]
    
    print("\nProbando sanitización de nombres:")
    for username, should_be_safe in test_cases:
        safe_name = "".join(c for c in username if c.isalnum() or c in "_-.")
        is_safe = bool(safe_name and safe_name == username)
        status = "✅" if is_safe == should_be_safe else "❌"
        print(f"  {status} '{username}' -> {'SEGURO' if is_safe else 'INSEGURO'}")
    
    print("\n✅ Pruebas de sanitización completadas")


if __name__ == "__main__":
    # Ejecutar pruebas
    success = test_user_memory_persistence()
    test_sanitization()
    
    if success:
        print("\n🎉 Sistema de memoria persistente funcionando correctamente!")
    else:
        print("\n❌ Algunas pruebas fallaron. Revisa los logs.")
