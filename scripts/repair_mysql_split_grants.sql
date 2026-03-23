-- SCRIPT UNICO DE REFERENCIA (GUIA FUTURA)
-- Reparacion de privilegios para separacion de bases de datos
-- Objetivo:
--   - FCFMUCHILE: personal y departamentos (authz/login)
--   - ai_support: system_prompts (prompts dinamicos)
--
-- Ejecutar como usuario con privilegios administrativos en MySQL.

-- =====================================================================
-- 1) Usuario de aplicacion para consultas de usuarios/departamentos
-- =====================================================================
-- Si el usuario ya existe, CREATE USER puede fallar y se puede omitir.
CREATE USER IF NOT EXISTS 'ai_support_user'@'%' IDENTIFIED BY 'REEMPLAZAR_PASSWORD_SEGURA';

-- Permisos minimos para flujo de login y perfil.
GRANT SELECT, INSERT, UPDATE ON `FCFMUCHILE`.`personal` TO 'ai_support_user'@'%';
GRANT SELECT ON `FCFMUCHILE`.`departamentos` TO 'ai_support_user'@'%';

-- =====================================================================
-- 2) Misma cuenta para prompts en DB ai_support
-- =====================================================================
-- Si quieres minima superficie, limita a system_prompts en vez de ai_support.*
GRANT SELECT, INSERT, UPDATE ON `ai_support`.`system_prompts` TO 'ai_support_user'@'%';

-- =====================================================================
-- 2.1) Persistencia de memoria conversacional (tabla ai_support_user_memory)
-- =====================================================================
-- Necesario cuando AI_SUPPORT_USER_MEMORY_BACKEND=mysql o auto con MySQL habilitado.
CREATE TABLE IF NOT EXISTS `ai_support`.`ai_support_user_memory` (
	`user_id` VARCHAR(128) NOT NULL,
	`last_updated` DATETIME(6) NOT NULL,
	`memory_json` JSON NOT NULL,
	`version` VARCHAR(16) NOT NULL,
	PRIMARY KEY (`user_id`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

GRANT SELECT, INSERT, UPDATE, DELETE ON `ai_support`.`ai_support_user_memory` TO 'ai_support_user'@'%';

-- =====================================================================
-- 3) Aplicar cambios
-- =====================================================================
FLUSH PRIVILEGES;

-- =====================================================================
-- 4) Verificacion sugerida
-- =====================================================================
-- SHOW GRANTS FOR 'ai_support_user'@'%';
