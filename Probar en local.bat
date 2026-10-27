@echo off
rem Sirve esta carpeta en http://localhost:8000/ y abre el navegador.
rem Hace falta un servidor (aunque sea local): los navegadores no cargan
rem modulos ni workers abriendo index.html con doble clic.
cd /d "%~dp0"
start "" cmd /c "timeout /t 2 >nul & start http://localhost:8000/"
python -m http.server 8000
if errorlevel 1 (
  echo.
  echo No se pudo arrancar el servidor. Comprueba que Python esta instalado
  echo y que el puerto 8000 no lo esta usando otro programa.
  pause
)
