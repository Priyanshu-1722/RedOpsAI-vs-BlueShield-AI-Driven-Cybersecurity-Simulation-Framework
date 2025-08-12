@echo off
title RedOps AI Installer
color 0A

echo [*] Creating RedOpsAI folder at C:\RedOpsAI
mkdir "C:\RedOpsAI"

echo [*] Copying scripts...
xcopy ".\files\*" "C:\RedOpsAI" /E /Y

echo [*] Checking Python installation...
where python >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Please install Python manually from https://www.python.org/downloads/
    pause
    exit /b
)

echo [*] Installing required Python packages...
python -m pip install --upgrade pip
python -m pip install schedule

echo [*] Creating daily scheduled task...
schtasks /create /tn "RedOpsAI_Daily_FineTune" /tr "C:\RedOpsAI\schedule_finetune.bat" /sc daily /st 10:00 /rl HIGHEST /f

echo [✔] Installation completed successfully!
pause
