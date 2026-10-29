@echo off
REM ============================================================
REM  start_all_servers.bat
REM  Starts all four processes in separate terminal windows.
REM
REM  USAGE:
REM    Double-click OR run from the project root directory.
REM
REM  REQUIRES:
REM    Python 3.8+ installed and on PATH
REM    pip install -r requirements.txt  (run once before first use)
REM ============================================================

title Distributed E-Commerce Startup

echo.
echo  =====================================================
echo   DISTRIBUTED E-COMMERCE — LOAD BALANCING DEMO
echo  =====================================================
echo.
echo  Starting all server processes...
echo  Each process opens in its own terminal window.
echo.

REM ── Server Node 1 (Port 5001) ─────────────────────────────────────────────
echo  [1/4] Starting Server Node 1 on port 5001...
start "Server Node 1 [:5001]" cmd /k "cd /d %~dp0server_node_1 && python app.py"

REM Small delay so nodes initialise the DB before load balancer connects
timeout /t 2 /nobreak >nul

REM ── Server Node 2 (Port 5002) ─────────────────────────────────────────────
echo  [2/4] Starting Server Node 2 on port 5002...
start "Server Node 2 [:5002]" cmd /k "cd /d %~dp0server_node_2 && python app.py"

timeout /t 1 /nobreak >nul

REM ── Server Node 3 (Port 5003) ─────────────────────────────────────────────
echo  [3/4] Starting Server Node 3 on port 5003...
start "Server Node 3 [:5003]" cmd /k "cd /d %~dp0server_node_3 && python app.py"

timeout /t 2 /nobreak >nul

REM ── Load Balancer (Port 5000) ──────────────────────────────────────────────
echo  [4/4] Starting Load Balancer on port 5000...
start "Load Balancer [:5000]" cmd /k "cd /d %~dp0load_balancer && python app.py"

timeout /t 3 /nobreak >nul

echo.
echo  =====================================================
echo   ALL SERVERS STARTED
echo  =====================================================
echo.
echo   Load Balancer  :  http://localhost:5000
echo   Server Node 1  :  http://localhost:5001
echo   Server Node 2  :  http://localhost:5002
echo   Server Node 3  :  http://localhost:5003
echo.
echo   Open your browser at:  http://localhost:5000
echo.
echo   To stop: close each terminal window individually.
echo  =====================================================
echo.

REM Open the browser automatically
start "" "http://localhost:5000"

pause
