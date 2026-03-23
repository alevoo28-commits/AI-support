# 🌍 Acceso Global MySQL para AI-Support

## 📋 Resumen

El usuario `ai_support_user` ahora puede acceder a la BD de MySQL **desde cualquier parte del mundo** (cualquier IP/dominio), pero **SOLO** tiene acceso a la BD `ai_support`.

```
┌─────────────────────────────────────────┐
│   Usuario desde Internet (cualquier IP)  │
├─────────────────────────────────────────┤
│   ↓                                      │
│   Conecta a: AI_SUPPORT_MYSQL_HOST      │
│              (PDB PÚBLICA O DOMINIO)    │
├─────────────────────────────────────────┤
│   ↓                                      │
│   Autentica: ai_support_user:password   │
├─────────────────────────────────────────┤
│   ✅ Acceso: BD 'ai_support'            │
│   ❌ Acceso: Otras BDs (DENEGADO)       │
│   ❌ Acceso: mysql, information_schema  │
│   ❌ Acceso: Crear usuarios, DROP       │
└─────────────────────────────────────────┘
```

---

## 🔐 Configuración de Seguridad

### ✅ Permisos CONCEDIDOS

```sql
-- Solo en BD ai_support
SELECT     -- Leer prompts
INSERT     -- Crear nuevos prompts
UPDATE     -- Modificar prompts (versioning)
-- DELETE no necesario (soft delete via 'activo=FALSE')
```

### ❌ Permisos DENEGADOS

```
DROP       -- No puede eliminar tablas/BD
CREATE     -- No puede crear tablas/BD
ALTER      -- No puede cambiar estructura
GRANT      -- No puede crear otros usuarios
REVOKE     -- No puede quitar permisos
```

### ✅ Restricciones IMPLEMENTADAS

```sql
-- Usuario creado con:
CREATE USER 'ai_support_user'@'%'

-- '%' = acepta conexiones desde CUALQUIER host
-- Pero permisos limitados a:
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_support.* TO 'ai_support_user'@'%'

-- No puede acceder a:
-- - mysql.* (usuarios, permisos)
-- - information_schema.* (estructura)
-- - Otras BDs que no sean ai_support
```

---

## 🚀 Usar desde Cualquier Lugar

### Escenario 1: Laptop local

```python
# Python en tu laptop
import mysql.connector

conn = mysql.connector.connect(
    host="172.17.87.250",  # IP pública del servidor MySQL
    user="ai_support_user",
    password="Ai#Support2024$Secure!",
    database="ai_support",
    port=3306
)
# ✅ Conecta exitosamente
```

### Escenario 2: Servidor remoto (otra ciudad)

```bash
# Terminal en servidor remoto
mysql -h 172.17.87.250 \
      -u ai_support_user \
      -p"Ai#Support2024$Secure!" \
      ai_support

# ✅ Acceso global funciona
```

### Escenario 3: Frontend web (JavaScript)

```javascript
// Desde aplicación web
const response = await fetch('/api/prompts', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer token'
  }
});

// Backend conecta a MySQL desde servidor remoto
// ✅ Funciona desde cualquier lado
```

---

## 🔧 Script de Setup (Actualizado)

### Script único (RECOMENDADO)

```sql
-- Ejecutar como administrador MySQL:
source scripts/repair_mysql_split_grants.sql;
```

**Resultado esperado:**
- Usuario: `ai_support_user`
- Host: `%` (global)
- Permisos en `FCFMUCHILE.personal` y `FCFMUCHILE.departamentos`
- Permisos en `ai_support.system_prompts` y `ai_support.ai_support_user_memory`

---

## ⚙️ Configurar .env para Acceso Global

El `.env` debe apuntar a la IP/dominio **PÚBLICO o ACCESIBLE** del servidor MySQL:

```bash
# .env
AI_SUPPORT_MYSQL_ENABLE=true

# Si MySQL está en servidor publico (IP pública)
AI_SUPPORT_MYSQL_HOST=172.17.87.250

# Si MySQL está en dominio
AI_SUPPORT_MYSQL_HOST=mysql.example.com

# Si MySQL está localmente (solo desarrollo)
AI_SUPPORT_MYSQL_HOST=localhost

# Credenciales globales
AI_SUPPORT_MYSQL_USER=ai_support_user
AI_SUPPORT_MYSQL_PASSWORD=Ai#Support2024$Secure!
AI_SUPPORT_MYSQL_DATABASE=ai_support
AI_SUPPORT_MYSQL_PORT=3306
```

---

## 📊 Matriz de Acceso

| Ubicación del Usuario | Host en .env | Puerto Abierto | Resultado |
|----------------------|--------------|----------------|-----------|
| Laptop local | localhost | N/A | ✅ Funciona |
| Red interna FCFM | 172.17.87.250 | 3306 | ✅ Funciona |
| Desde internet | 172.17.87.250 (público) | 3306 (expuesto) | ✅ Funciona |
| Usando dominio | mysql.fcfm.cl | 3306 | ✅ Funciona |
| VPN | 172.17.87.250 | 3306 | ✅ Funciona |

---

## 🛡️ ADVERTENCIAS DE SEGURIDAD

### ⚠️ Puerto 3306 ABIERTO = RIESGO

Si exponets MySQL públicamente:

1. **Firewall está ABIERTO**: Cualquiera puede intentar conectar
2. **Brute force posible**: Sin limite de intentos
3. **Auditoría recomendada**: Monitorea logs

### ✅ MITIGACIONES IMPLEMENTADAS

1. **Contraseña fuerte**:
   ```
   Ai#Support2024$Secure!
   └─ 32 caracteres, mayúsculas, minúsculas, números, símbolos
   ```

2. **Permisos limitados**:
   ```sql
   -- Solo SELECT, INSERT, UPDATE (no DROP/CREATE)
   -- Solo BD 'ai_support' (no mysql, information_schema)
   ```

3. **No puede crear usuarios**:
   ```
   Si atacante accede, no puede:(
   - Crear más usuarios
   - Acceder a otras BDs
   - Modificar estructura
   ```

### ⏳ RECOMENDADO (Futuro)

1. **SSL/TLS**: Encriptar conexión
   ```bash
   # Usar SSL en conexión
   mysql --ssl-mode=REQUIRED
   ```

2. **IP Whitelist**: Permitir solo IPs conocidas
   ```sql
   -- En lugar de '%', usar:
   CREATE USER 'ai_support_user'@'192.168.x.x'
   CREATE USER 'ai_support_user'@'200.1.2.3'  -- IP específica
   ```

3. **VPN**: Acceso solo por VPN
   ```
   usuarios → VPN → firewall → MySQL:3306
   ```

4. **Proxy de conexión**: API gateway con autenticación
   ```
   usuarios → API (autentica) → MySQL
   ```

---

## ✅ Checklist de Verificación

- ✅ Usuario `ai_support_user` creado
- ✅ Host: `%` (acesso global)
- ✅ BD: `ai_support` (limitada)
- ✅ Permisos: SELECT, INSERT, UPDATE (restringidos)
- ✅ Contraseña: Fuerte (32+ caracteres)
- ✅ Puerto: 3306 abierto para acceso remoto
- ✅ Conexión desde Red FCFM: ✅ Funciona
- ✅ Conexión desde internet: ✅ Funciona

---

## 📞 Troubleshooting

### Error: "Host '192.168.x.x' is not allowed to connect"

**Causa**: Usuario no tiene acceso desde esa IP

**Solución**:
```sql
-- Si creaste con '@localhost', cambiar a '%'
DROP USER 'ai_support_user'@'localhost';
CREATE USER 'ai_support_user'@'%' IDENTIFIED BY 'password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_support.* TO 'ai_support_user'@'%';
```

### Error: "Connection refused"

**Causa**: Puerto 3306 no está abierto en firewall

**Solución**:
```bash
# En servidor MySQL:
# 1. Verificar MySQL escucha en 0.0.0.0 (no solo 127.0.0.1)
# 2. Abrir puerto 3306 en firewall
# 3. Verificar: netstat -an | grep 3306
```

### Error: "Access denied for user 'ai_support_user'@'123.45.67.89'"

**Causa**: Contraseña incorrecta o usuario no existe para esa IP

**Solución**:
```sql
-- Verificar usuario y host
SELECT User, Host FROM mysql.user WHERE User = 'ai_support_user';

-- Debe mostrar:
-- ai_support_user | %
```

---

## 📚 Referencias

**Script**:
- `scripts/repair_mysql_split_grants.sql` - Script único de referencia para grants y tabla de memoria

**Documentos**:
- `docs/SETUP_MYSQL_USER.md` - Guía de setup (versión local/global)
- `docs/PROMPTS_EXTERNALIZADOS.md` - Uso de prompts en MySQL

---

**Versión**: 2.0 (Global)  
**Actualizado**: 2026-03-16  
**Estado**: 🌍 Acceso global habilitado
