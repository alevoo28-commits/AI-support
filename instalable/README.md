# instalable

Instalable es una herramienta para Windows que diagnostica y soluciona problemas de conectividad de red, asignando IPs de forma inteligente y automática según la configuración de la base de datos y el segmento de red.

## Requisitos
- Windows 10/11
- Python 3.8+
- Permisos de administrador

## Instalación y uso
1. Configura el archivo `.env` con tus credenciales y parámetros de red.
2. Instala las dependencias: `pip install -r requirements.txt`
3. Ejecuta el script principal o genera el ejecutable con PyInstaller.

## Segmentos de red soportados
- 172.17.82.xxx
- 172.17.83.xxx
- 172.17.84.xxx
- 172.17.85.xxx
- 172.17.86.xxx
- 172.17.87.xxx

DNS por defecto: 172.17.66.9, 172.17.40.9

## Flujo de ejecución
1. Verifica conectividad a Internet.
2. Si no hay conexión, revisa IP actual.
3. Consulta la base de datos para IPs usadas.
4. Busca y asigna una IP libre en el segmento adecuado.
5. Aplica la configuración de red y verifica conectividad.

## Licencia
MIT
