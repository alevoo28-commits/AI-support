-- Script SQL: Crear usuario MySQL para AI-Support
-- Ejecutar como root en MySQL

-- ============================================================
-- 1. CREAR USUARIO Y CONTRASEÑA
-- ============================================================

-- Crear usuario 'ai_support_user' con host localhost
CREATE USER IF NOT EXISTS 'ai_support_user'@'localhost' IDENTIFIED BY 'Ai#Support2024$Secure!';

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS ai_support CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ============================================================
-- 2. OTORGAR PERMISOS ESPECÍFICOS
-- ============================================================

-- Permisos en la BD ai_support (tabla system_prompts)
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_support.* TO 'ai_support_user'@'localhost';

-- Permisos específicos en system_prompts (futuro)
GRANT SELECT ON ai_support.system_prompts TO 'ai_support_user'@'localhost';
GRANT INSERT ON ai_support.system_prompts TO 'ai_support_user'@'localhost';
GRANT UPDATE ON ai_support.system_prompts TO 'ai_support_user'@'localhost';

-- ============================================================
-- 3. APLICAR CAMBIOS
-- ============================================================

FLUSH PRIVILEGES;

-- ============================================================
-- 4. VERIFICACIÓN
-- ============================================================

-- Ver usuario creado
SELECT User, Host, authentication_string FROM mysql.user WHERE User = 'ai_support_user';

-- Ver permisos del usuario
SHOW GRANTS FOR 'ai_support_user'@'localhost';

-- ============================================================
-- CREDENCIALES PARA .env
-- ============================================================
-- AI_SUPPORT_MYSQL_HOST=localhost
-- AI_SUPPORT_MYSQL_USER=ai_support_user
-- AI_SUPPORT_MYSQL_PASSWORD=Ai#Support2024$Secure!
-- AI_SUPPORT_MYSQL_DATABASE=ai_support
-- AI_SUPPORT_MYSQL_PORT=3306
-- AI_SUPPORT_MYSQL_ENABLE=true
