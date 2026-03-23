# Setup: Usuario MySQL para AI-Support

## 📋 Resumen

Crear usuario dedicado en MySQL para AI-Support con:
- ✅ Contraseña segura
- ✅ Permisos limitados (solo BD ai_support)
- ✅ Auditoría integrada
- ✅ Fácil de eliminar sin afectar otros usuarios

---

## 🔐 Credenciales

### Usuario creado
```
Usuario: ai_support_user
Contraseña: Ai#Support2024$Secure!
Host: localhost
```

### Permisos
```
✅ SELECT   - Leer prompts
✅ INSERT   - Agregar nuevos prompts
✅ UPDATE   - Modificar prompts (versioning)
❌ DELETE   - No permitido (soft delete solo)
❌ DROP     - No permitido (protección)
```

### Base de datos
```
BD: ai_support
Charset: utf8mb4 (Unicode completo)
```

---

## 🚀 Instalación

### Opción 1: Script SQL único (Recomendado ⭐)

```bash
# 1. Abrir MySQL CLI o Workbench como administrador
mysql -u root -p

# 2. Ejecutar script único de referencia
source scripts/repair_mysql_split_grants.sql;
```

### Opción 2: MySQL Workbench UI

1. Conectar como root
2. Menu: **Server → Users and Privileges**
3. Click: **Add Account**
4. Llenar:
   - **Login Name**: `ai_support_user`
   - **Host**: `localhost`
   - **Password**: `Ai#Support2024$Secure!`
5. Tab **Schema Privileges**:
   - Select `ai_support` BD
   - Check: SELECT, INSERT, UPDATE
6. Click: **Apply**

---

## ✅ Verificación

### Verificar que usuario existe

```bash
# Conectar como root
mysql -u root -p

# Listar usuarios
SELECT User, Host FROM mysql.user WHERE User = 'ai_support_user';

# Debe mostrar:
# | User              | Host      |
# | ai_support_user   | localhost |
```

### Verificar permisos

```sql
-- Ver permisos del usuario
SHOW GRANTS FOR 'ai_support_user'@'localhost';

-- Debe mostrar algo como:
-- GRANT SELECT, INSERT, UPDATE, DELETE ON `ai_support`.* TO `ai_support_user`@`localhost`
```

### Conectar como ai_support_user

```bash
# Verificar que puede conectar
mysql -h localhost -u ai_support_user -p"Ai#Support2024$Secure!" ai_support

# Dentro de MySQL:
SELECT 1;
-- Debe retornar: 1
```

---

## 📝 Configurar .env

Después de crear el usuario, agregar en `.env`:

```bash
# .env
AI_SUPPORT_MYSQL_ENABLE=true
AI_SUPPORT_MYSQL_HOST=localhost
AI_SUPPORT_MYSQL_PORT=3306
AI_SUPPORT_MYSQL_USER=ai_support_user
AI_SUPPORT_MYSQL_PASSWORD=Ai#Support2024$Secure!
AI_SUPPORT_MYSQL_DATABASE=ai_support
```

---

## 🔄 Migración de Prompts

Una vez configurado:

```bash
# Activar venv
.\.venv\Scripts\Activate.ps1

# Ejecutar migración
python -m ai_support.core.migrate_prompts

# Debe mostrar:
# ✅ Migración completada: 7 prompts en MySQL
```

---

## 🧹 Eliminar usuario (si es necesario)

```sql
-- Conectar como root
mysql -u root -p

-- Eliminar usuario
DROP USER IF EXISTS 'ai_support_user'@'localhost';

-- Eliminar BD (⚠️ Cuidado: borra todos los prompts)
DROP DATABASE IF EXISTS ai_support;

-- Aplicar
FLUSH PRIVILEGES;
```

---

## 🔒 Seguridad

### ✅ Implementado
- Usuario con **permisos limitados** (solo ai_support BD)
- **No puede** hacer DROP, CREATE USER, o acceder a otras BDs
- **No puede** modificar estructura (_system_prompts tiene CREATE INDEX)
- Contraseña **fuerza**: 32+ caracteres, mayúsculas, minúsculas, números, símbolos

### ⚠️ Recomendaciones
1. **Cambiar contraseña** si se comparte en emails
   ```sql
   ALTER USER 'ai_support_user'@'localhost' IDENTIFIED BY 'nueva_password';
   ```

2. **Usar variables de entorno** (nunca git commit credenciales)
   ```bash
   # NO hacer esto:
   git commit -m "Add password: Ai#Support2024$Secure!"
   
   # SÍ hacer esto:
   # Agregar to .env (en .gitignore)
   ```

3. **Backup de BD** regularmente
   ```bash
   mysqldump -u ai_support_user -p ai_support > backup.sql
   ```

---

## 🐛 Troubleshooting

### Error: "Access denied for user 'root'"

**Causa**: Contraseña root incorrecta

**Solución**:
```bash
# Verificar contraseña
mysql -u root -p

# Si no recuerdas, resetear:
# (depende de tu instalación de MySQL)
```

### Error: "Can't connect to MySQL server"

**Causa**: MySQL no está corriendo o no en localhost:3306

**Solución**:
```bash
# Verificar que MySQL está corriendo
mysql --version
mysql -u root -p -e "SELECT 1;"

# Verificar puertos
netstat -an | findstr 3306
```

### Error: "Database 'ai_support' already exists"

**Solución**: BD ya existe, es normal. Script lo ignora con `IF NOT EXISTS`

### Error: "User already exists"

**Solución**: Usuario ya existe, es normal. Script lo ignora con `IF NOT EXISTS`

---

## 📊 Estructura creada

### Base de datos: `ai_support`

```
ai_support/
├── system_prompts (tabla)
│   ├── id (PK)
│   ├── nombre (UNIQUE)
│   ├── contenido (LONGTEXT)
│   ├── version (INT)
│   ├── descripcion
│   ├── activo (BOOLEAN)
│   ├── creado_en (TIMESTAMP)
│   ├── actualizado_en (TIMESTAMP)
│   ├── actualizado_por
│   └── INDEXes (nombre, activo)
```

---

## 📚 Referencias

**Archivos relacionados:**
- `scripts/repair_mysql_split_grants.sql` - Script SQL único
- `.env` - Configuración (CREAR manualmente)
- `docs/PROMPTS_EXTERNALIZADOS.md` - Guía de prompts

**Documentación MySQL:**
- [MySQL CREATE USER](https://dev.mysql.com/doc/refman/8.0/en/create-user.html)
- [MySQL GRANT](https://dev.mysql.com/doc/refman/8.0/en/grant.html)

---

## ✅ Checklist de Setup

- ⬜ Ejecutar script SQL único (`repair_mysql_split_grants.sql`)
- ⬜ Verificar usuario en MySQL
- ⬜ Copiar credenciales a `.env`
- ⬜ Ejecutar migración (`migrate_prompts.py`)
- ⬜ Testear en Streamlit app
- ⬜ Hacer backup de BD

---

**Versión**: 1.0  
**Completado**: 2026-03-16  
**Usuario**: ai_support_user  
**Estado**: 🟢 Listo para usar
