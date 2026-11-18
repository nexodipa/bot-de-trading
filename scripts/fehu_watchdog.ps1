<#
.SYNOPSIS
    Proyecto Fehu (ᚠ) - Watchdog Supervisor de Producción para Windows.
    Vigila los procesos críticos (Panel Multi-Broker en puerto 8770 y Live-Loop 24/7)
    y los reinicia automáticamente ante caídas o tras reinicios del sistema.
#>
param(
    [switch]$Once,
    [int]$CheckIntervalSeconds = 30
)

$ErrorActionPreference = "SilentlyContinue"
$RepoDir = "C:\Users\USUARIO\bot de trading"
$PythonExe = Join-Path $RepoDir "venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = Join-Path $RepoDir "venv\Scripts\python.exe"
}
$LogFile = Join-Path $RepoDir "watchdog.log"

function Write-WatchdogLog {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts [WATCHDOG] $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Test-BotProcessRunning {
    param([string]$Pattern)
    $procs = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" |
        Where-Object { $_.CommandLine -like "*$Pattern*" }
    return ($null -ne $procs -and @($procs).Count -gt 0)
}

Write-WatchdogLog "Supervisor iniciado (Once=$Once, Intervalo=${CheckIntervalSeconds}s)."

while ($true) {
    # 1. Verificar Panel Web (Puerto 8770)
    if (-not (Test-BotProcessRunning -Pattern "main.py panel")) {
        Write-WatchdogLog "Panel Multi-Broker no detectado. Iniciando en 127.0.0.1:8770..."
        Start-Process -FilePath $PythonExe `
            -ArgumentList "main.py", "panel", "--host", "127.0.0.1", "--port", "8770" `
            -WorkingDirectory $RepoDir `
            -WindowStyle Hidden
    }

    # 2. Verificar Bucle de Trading en Vivo (24/7)
    if (-not (Test-BotProcessRunning -Pattern "main.py live-loop")) {
        Write-WatchdogLog "Live-Loop no detectado. Iniciando bucle de ejecucion 24/7..."
        Start-Process -FilePath $PythonExe `
            -ArgumentList "main.py", "live-loop", "--confirm-live", "I_UNDERSTAND_LIVE_RISK", "--sleep-seconds", "300" `
            -WorkingDirectory $RepoDir `
            -WindowStyle Hidden
    }

    if ($Once) {
        break
    }
    Start-Sleep -Seconds $CheckIntervalSeconds
}
