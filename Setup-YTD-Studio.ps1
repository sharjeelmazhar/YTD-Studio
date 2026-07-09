#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$InstallDir = "C:\YTD Studio"
$DownloadRoot = Join-Path $env:USERPROFILE "Downloads\YTD Studio Downloads"
$TaskName = "YTD Studio"
$Port = 8501
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-UvCommand {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $paths = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe")
    )

    foreach ($path in $paths) {
        if (Test-Path -LiteralPath $path) {
            return $path
        }
    }

    return $null
}

function Stop-YtdStudioProcesses {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -like "*C:\YTD Studio*" -or
                $_.CommandLine -like "*streamlit run app.py*" -or
                $_.CommandLine -like "*Start-YTD-Studio*"
            )
        } |
        ForEach-Object {
            if ($_.ProcessId -ne $PID) {
                try {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
                    Write-Host "Stopped process $($_.ProcessId): $($_.Name)"
                }
                catch {
                    Write-Host "Could not stop process $($_.ProcessId): $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
        }
}

function Remove-YtdTask {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed old task: $TaskName"
    }
}

function Wait-ForWebApp {
    param(
        [int]$Seconds = 45
    )

    $deadline = (Get-Date).AddSeconds($Seconds)

    while ((Get-Date) -lt $deadline) {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listener) {
            return $true
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

if (-not (Test-Administrator)) {
    Write-Host "Please run this setup from an Administrator PowerShell or Windows Terminal." -ForegroundColor Red
    Write-Host "Example:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 1
}

Write-Step "Checking source folder"
$requiredFiles = @("app.py", "downloader.py", "pyproject.toml", "uv.lock", "README.md")
foreach ($file in $requiredFiles) {
    $path = Join-Path $SourceDir $file
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required file: $path"
    }
}

Write-Step "Checking UV"
$UvPath = Get-UvCommand
if (-not $UvPath) {
    Write-Host "UV was not found. Installing UV with Astral's official Windows installer..."
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
    $UvPath = Get-UvCommand
}

if (-not $UvPath) {
    throw "UV installation finished, but uv.exe was not found. Close this terminal, open a new Administrator terminal, and run setup again."
}
Write-Host "Using UV: $UvPath" -ForegroundColor Green

Write-Step "Stopping old app and task"
Remove-YtdTask
Stop-YtdStudioProcesses

Write-Step "Creating folders"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DownloadRoot "video") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DownloadRoot "audio") | Out-Null

Write-Step "Copying app files to $InstallDir"
$excludeDirs = @(".git", ".venv", "__pycache__", "downloads", ".codex-remote-attachments")
$excludeFiles = @("*.pyc", "*.pyo", ".DS_Store", "download-history.json", "ytd-studio.log", "*.zip")
$robocopyArgs = @(
    "`"$SourceDir`"",
    "`"$InstallDir`"",
    "/MIR",
    "/XD"
) + ($excludeDirs | ForEach-Object { "`"$SourceDir\$_`"" }) + @(
    "/XF"
) + $excludeFiles + @(
    "/R:2",
    "/W:1",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS"
)

cmd.exe /c ("robocopy " + ($robocopyArgs -join " ")) | Out-Host
if ($LASTEXITCODE -gt 7) {
    throw "Robocopy failed with exit code $LASTEXITCODE."
}

Write-Step "Syncing Python environment with UV"
Push-Location $InstallDir
try {
    & $UvPath sync
}
finally {
    Pop-Location
}

Write-Step "Writing launcher files"
$LauncherPath = Join-Path $InstallDir "Start-YTD-Studio.ps1"
$HiddenLauncherPath = Join-Path $InstallDir "Start-YTD-Studio-Hidden.vbs"
$LinksPath = Join-Path $InstallDir "Show-YTD-Studio-Links.ps1"
$LogPath = Join-Path $InstallDir "ytd-studio.log"

$LinksScript = @"
`$ErrorActionPreference = "SilentlyContinue"
`$Port = $Port
`$Desktop = [Environment]::GetFolderPath("Desktop")
`$LocalUrl = "http://localhost:`$Port"
`$HostUrl = "http://`$(`$env:COMPUTERNAME):`$Port"
`$IpAddresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        `$_.IPAddress -notlike "127.*" -and
        `$_.IPAddress -notlike "169.254.*" -and
        `$_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object InterfaceMetric, InterfaceIndex |
    Select-Object -ExpandProperty IPAddress -Unique

`$Lines = @(
    "YTD Studio links",
    "",
    "This computer:",
    "  `$LocalUrl",
    "",
    "Try this from another device on the same Wi-Fi first:",
    "  `$HostUrl",
    "",
    "Current network IP links:"
)

if (`$IpAddresses) {
    foreach (`$Ip in `$IpAddresses) {
        `$Lines += "  http://`$(`$Ip):`$Port"
    }
}
else {
    `$Lines += "  No active Wi-Fi/Ethernet IPv4 address found."
}

`$Lines += ""
`$Lines += "If you change Wi-Fi networks, run this file again:"
`$Lines += "  C:\YTD Studio\Show-YTD-Studio-Links.ps1"
`$Lines += ""
`$Lines += "The app must be running on the Windows computer, and both devices must be on the same network."

`$OutputFile = Join-Path `$Desktop "YTD Studio Links.txt"
`$Lines | Set-Content -Path `$OutputFile -Encoding UTF8
"[InternetShortcut]`r`nURL=`$LocalUrl`r`n" | Set-Content -Path (Join-Path `$Desktop "YTD Studio.url") -Encoding ASCII

`$Lines | ForEach-Object { Write-Host `$_ }
"@
Set-Content -Path $LinksPath -Value $LinksScript -Encoding UTF8

$Launcher = @"
`$ErrorActionPreference = "Stop"
`$AppDir = "C:\YTD Studio"
`$UvExe = "$UvPath"
`$Port = $Port
`$LogPath = "$LogPath"
`$LinksPath = "$LinksPath"

function Write-Log {
    param([string]`$Message)
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "`$timestamp  `$Message" | Add-Content -Path `$LogPath -Encoding UTF8
}

try {
    `$env:PATH = "`$env:USERPROFILE\.local\bin;`$env:USERPROFILE\.cargo\bin;`$env:PATH"
    Set-Location `$AppDir

    "============================================================" | Add-Content -Path `$LogPath -Encoding UTF8
    Write-Log "Launcher started as `$env:USERNAME."

    if (-not (Test-Path -LiteralPath `$UvExe)) {
        throw "UV executable not found at `$UvExe"
    }
    if (-not (Test-Path -LiteralPath (Join-Path `$AppDir "app.py"))) {
        throw "app.py not found in `$AppDir"
    }

    & `$LinksPath *> `$null

    `$listener = Get-NetTCPConnection -LocalPort `$Port -State Listen -ErrorAction SilentlyContinue
    if (`$listener) {
        Write-Log "Port `$Port is already listening. Launcher exiting to avoid duplicate app instances."
        exit 0
    }

    Write-Log "Starting Streamlit on http://localhost:`$Port and http://0.0.0.0:`$Port"
    & `$UvExe run streamlit run app.py --server.headless=true --server.address=0.0.0.0 --server.port=`$Port --browser.gatherUsageStats=false --server.fileWatcherType=none *>> `$LogPath
    Write-Log "Streamlit process exited with code `$LASTEXITCODE."
    exit `$LASTEXITCODE
}
catch {
    Write-Log "Startup failed: `$(`$_.Exception.Message)"
    Write-Log "Full error: `$(`$_ | Out-String)"
    exit 1
}
"@
Set-Content -Path $LauncherPath -Value $Launcher -Encoding UTF8

$HiddenLauncher = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$LauncherPath""", 0, False
"@
Set-Content -Path $HiddenLauncherPath -Value $HiddenLauncher -Encoding ASCII

Write-Step "Registering hidden Windows startup task"
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$HiddenLauncherPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Step "Starting YTD Studio now"
Start-ScheduledTask -TaskName $TaskName

if (-not (Wait-ForWebApp -Seconds 120)) {
    Write-Host "YTD Studio did not start listening at http://localhost:$($Port) within 120 seconds." -ForegroundColor Red
    Write-Host ""
    Write-Host "Last log lines from $($LogPath):" -ForegroundColor Yellow
    if (Test-Path -LiteralPath $LogPath) {
        Get-Content -LiteralPath $LogPath -Tail 120
    }
    else {
        Write-Host "No log file was created."
    }
    throw "Startup health check failed."
}

& $LinksPath | Out-Host

Write-Host ""
Write-Host "YTD Studio setup complete." -ForegroundColor Green
Write-Host "Installed app: $InstallDir"
Write-Host "Downloads folder: $DownloadRoot"
Write-Host "Local URL: http://localhost:$($Port)"
Write-Host "Startup task: $TaskName"
Write-Host "Log file: $LogPath"
Write-Host "Network links are saved on Desktop: YTD Studio Links.txt"
Write-Host ""
Write-Host "Load the browser extension manually from:"
Write-Host "  $InstallDir\extension"
