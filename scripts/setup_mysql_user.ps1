#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup de usuario MySQL para AI-Support con acceso GLOBAL
    
.DESCRIPTION
    Crea usuario, BD y permisos para AI-Support
    - Acceso desde CUALQUIER IP (global)
    - Permisos limitados SOLO a BD 'ai_support'
    - Contraseña segura
    
.EXAMPLE
    .\setup_mysql_user.ps1 -MySQLRootPassword "your_root_password"
    
.NOTES
    Requiere: MySQL server running (localhost o remoto)
    Acceso: Global ('ai_support_user'@'%')
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$MySQLRootPassword,
    
    [Parameter(Mandatory=$false)]
    [string]$MySQLHost = "localhost",
    
    [Parameter(Mandatory=$false)]
    [int]$MySQLPort = 3306,
    
    [Parameter(Mandatory=$false)]
    [string]$AiSupportUser = "ai_support_user",
    
    [Parameter(Mandatory=$false)]
    [string]$AiSupportDatabase = "ai_support",
    
    [Parameter(Mandatory=$false)]
    [string]$AiSupportPassword = "Ai#Support2024`$Secure!",
    
    # NUEVO: Permitir acceso global (%)
    [Parameter(Mandatory=$false)]
    [string]$AllowHost = "%"  # "%" = cualquier IP, "localhost" = solo local
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{
        "Success" = "Green"
        "Error" = "Red"
        "Warning" = "Yellow"
        "Info" = "Cyan"
    }
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $colors[$Type]
}

try {
    Write-Status "🔧 Setup de usuario MySQL para AI-Support (ACCESO GLOBAL)" "Info"
    Write-Status "Host MySQL servidor: $MySQLHost" "Info"
    Write-Status "Port: $MySQLPort" "Info"
    Write-Status "Usuario: $AiSupportUser" "Info"
    Write-Status "Acceso desde: $AllowHost (% = desde cualquier IP)" "Info"
    Write-Status "BD: $AiSupportDatabase" "Info"
    Write-Status ""
    
    # Verificar que mysql-client esté disponible
    $mysqlCmd = Get-Command mysql -ErrorAction SilentlyContinue
    if (-not $mysqlCmd) {
        Write-Status "❌ MySQL client no encontrado. Instala mysql-shell o mysql-connector" "Error"
        exit 1
    }
    
    Write-Status "✅ MySQL client encontrado: $($mysqlCmd.Source)" "Success"
    
    # Preparar SQL (usar %AllowHost para permitir acceso global)
    $sqlCommands = @"
-- Crear usuario con acceso GLOBAL
CREATE USER IF NOT EXISTS '$AiSupportUser'@'$AllowHost' IDENTIFIED BY '$AiSupportPassword';

-- Crear BD
CREATE DATABASE IF NOT EXISTS $AiSupportDatabase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Permisos LIMITADOS a BD ai_support
GRANT SELECT, INSERT, UPDATE, DELETE ON $AiSupportDatabase.* TO '$AiSupportUser'@'$AllowHost';

-- Aplicar cambios
FLUSH PRIVILEGES;
"@
    
    Write-Status ""
    Write-Status "📝 Ejecutando SQL..." "Info"
    
    # Ejecutar comandos SQL
    $sqlCommands | mysql -h $MySQLHost -P $MySQLPort -u root -p"$MySQLRootPassword" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "✅ Usuario y BD creados exitosamente" "Success"
    } else {
        Write-Status "❌ Error al crear usuario" "Error"
        exit 1
    }
    
    # Verificar
    Write-Status ""
    Write-Status "🔍 Verificando..." "Info"
    
    $verifySQL = "SELECT User, Host FROM mysql.user WHERE User = '$AiSupportUser';"
    $result = $verifySQL | mysql -h $MySQLHost -P $MySQLPort -u root -p"$MySQLRootPassword" 2>&1
    
    if ($result -match $AiSupportUser) {
        Write-Status "✅ Usuario verificado en MySQL (Host: $AllowHost)" "Success"
    }
    
    # Generar .env
    Write-Status ""
    Write-Status "📝 Generando configuración para .env..." "Info"
    
    $envContent = @"
# ============================================================
# Configuración MySQL para AI-Support
# ============================================================
# ACCESO GLOBAL: El usuario puede conectar desde cualquier IP
# LIMITADO: Solo tiene acceso a BD 'ai_support'
# ============================================================

# Habilitar MySQL
AI_SUPPORT_MYSQL_ENABLE=true

# Conexión
# NOTA: Host puede ser IP pública, dominio, o localhost
# El usuario 'ai_support_user' puede conectar desde CUALQUIER IP
AI_SUPPORT_MYSQL_HOST=$MySQLHost
AI_SUPPORT_MYSQL_PORT=$MySQLPort
AI_SUPPORT_MYSQL_USER=$AiSupportUser
AI_SUPPORT_MYSQL_PASSWORD=$AiSupportPassword
AI_SUPPORT_MYSQL_DATABASE=$AiSupportDatabase
"@
    
    Write-Status ""
    Write-Status "📋 Copiar esto en tu .env:" "Warning"
    Write-Host "---" -ForegroundColor Yellow
    Write-Host $envContent -ForegroundColor Yellow
    Write-Host "---" -ForegroundColor Yellow
    
    Write-Status ""
    Write-Status "✅ Setup completado!" "Success"
    Write-Status ""
    Write-Status "📚 Próximos pasos:" "Info"
    Write-Status "1. Agregar la configuración anterior en .env" "Info"
    Write-Status "2. Ejecutar: python -m ai_support.core.migrate_prompts" "Info"
    Write-Status "3. Iniciar app: streamlit run ai_support/ui/streamlit_app.py" "Info"
    Write-Status ""
    
} catch {
    Write-Status "❌ Error: $_" "Error"
    exit 1
}
