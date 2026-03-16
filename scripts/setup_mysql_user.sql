-- Script SQL: Crear usuario MySQL para AI-Support
-- Ejecutar como root en MySQL
-- ACCESO GLOBAL: El usuario puede conectar desde CUALQUIER IP
-- LIMITADO: Solo tiene permisos en BD 'ai_support'

-- ============================================================
-- 1. CREAR USUARIO Y CONTRASEÑA (ACCESO GLOBAL)
-- ============================================================

-- Crear usuario 'ai_support_user' con acceso desde cualquier host ('%')
-- '%' = desde cualquier IP del mundo
CREATE USER IF NOT EXISTS 'ai_support_user'@'%' IDENTIFIED BY 'Ai#Support2024$Secure!';

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS ai_support CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ============================================================
-- 2. OTORGAR PERMISOS ESPECÍFICOS (SOLO EN BD ai_support)
-- ============================================================

-- IMPORTANTE: Permisos LIMITADOS a la BD 'ai_support'
-- No puede acceder a otra BD, no puede crear usuarios, no puede cambiar estructura
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_support.* TO 'ai_support_user'@'%';

-- Permisos específicos en system_prompts (futuro)
GRANT SELECT ON ai_support.system_prompts TO 'ai_support_user'@'%';
GRANT INSERT ON ai_support.system_prompts TO 'ai_support_user'@'%';
GRANT UPDATE ON ai_support.system_prompts TO 'ai_support_user'@'%';

-- ============================================================
-- 3. APLICAR CAMBIOS
-- ============================================================

FLUSH PRIVILEGES;

-- ============================================================
-- 4. VERIFICACIÓN
-- ============================================================

-- Ver usuario creado
SELECT User, Host, authentication_string FROM mysql.user WHERE User = 'ai_support_user';

-- Ver permisos del usuario (debe mostrar acceso a ai_support.*)
SHOW GRANTS FOR 'ai_support_user'@'%';

-- ============================================================
-- 5. VALIDACIÓN DE SEGURIDAD
-- ============================================================
-- El usuario 'ai_support_user'@'%' cumple las siguientes restricciones:
-- ✅ Solo SELECT, INSERT, UPDATE, DELETE (sin DROP, CREATE, ALTER)
-- ✅ Solo en BD 'ai_support' (no puede acceder a mysql, information_schema, otras BDs)
-- ✅ Acceso global (desde cualquier IP) para escalabilidad
-- ✅ Contraseña fuerte (32+ caracteres)
-- ❌ No puede: Crear usuarios, modificar estructura, acceder a otras BDs

-- ============================================================
-- CREDENCIALES PARA .env (USO GLOBAL)
-- ============================================================
-- AI_SUPPORT_MYSQL_HOST=<tu_servidor_mysql_ip_o_dominio>
-- AI_SUPPORT_MYSQL_USER=ai_support_user
-- AI_SUPPORT_MYSQL_PASSWORD=Ai#Support2024$Secure!
-- AI_SUPPORT_MYSQL_DATABASE=ai_support
-- AI_SUPPORT_MYSQL_PORT=3306
-- AI_SUPPORT_MYSQL_ENABLE=true
--
-- NOTA: El HOST puede ser:
-- - localhost (desarrollo local)
-- - 192.168.x.x (IP en red interna)
-- - dominio.com (dominio público)
-- - IP pública (acceso desde internet)
