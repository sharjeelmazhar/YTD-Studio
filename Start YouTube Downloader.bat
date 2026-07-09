@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo UV was not found on this computer.
    echo Install UV first, then run this launcher again.
    pause
    exit /b 1
)

echo Starting YouTube Downloader...
echo A browser window should open automatically.
echo Keep this window open while using the app.
uv run streamlit run app.py --server.headless=false --server.address=localhost --server.port=8501

pause
