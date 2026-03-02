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
python -m PyInstaller --onefile --console --name "ConfiguradorRed_FCFM" --icon=NONE src/main.py

echo.
echo ========================================
echo  Compilación completada
echo ========================================
echo.
echo El ejecutable se encuentra en: dist\ConfiguradorRed_FCFM.exe
echo.
pause
