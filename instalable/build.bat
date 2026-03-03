@echo off
echo ========================================
echo  Compilando Sistema de Red FCFM
echo ========================================
echo.

echo.
echo Compilando ejecutable...

echo Activando entorno virtual...
call .venv\Scripts\activate.bat

echo Instalando dependencias en entorno virtual...
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo.
echo Compilando ejecutable...
python -m PyInstaller --onefile --console ^
  --name "ConfiguradorRed_FCFM" ^
  --paths src ^
  --hidden-import mysql.connector ^
  src/main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Compilacion completada
echo ============================================
echo  Ejecutable : dist\ConfiguradorRed_FCFM.exe
echo.
echo  IMPORTANTE: Copia el archivo .env junto al
echo  ejecutable antes de distribuirlo.
echo  El .env debe contener:
echo    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
echo    DB_NAME, GATEWAY (opcional)
echo.
pause
