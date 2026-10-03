@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Prospect Signal needs Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating Prospect Signal's private Python environment...
  py -m venv .venv
)
".venv\Scripts\python.exe" -c "import streamlit, duckdb, truststore, yaml" >nul 2>&1
if errorlevel 1 (
  echo Installing Prospect Signal's open-source packages...
  ".venv\Scripts\python.exe" -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
if "%PROSPECTSIGNAL_PORT%"=="" set PROSPECTSIGNAL_PORT=8589
if "%PROSPECTSIGNAL_MAX_UPLOAD_MB%"=="" set PROSPECTSIGNAL_MAX_UPLOAD_MB=10000
echo Starting Prospect Signal at http://127.0.0.1:%PROSPECTSIGNAL_PORT% ...
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless=false --server.address=127.0.0.1 --server.port=%PROSPECTSIGNAL_PORT% --server.maxUploadSize=%PROSPECTSIGNAL_MAX_UPLOAD_MB% --server.fileWatcherType=none --browser.gatherUsageStats=false
if errorlevel 1 pause
