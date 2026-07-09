#Requires -Version 5.1

$ErrorActionPreference = "Stop"

$InstallDir = "C:\YTD Studio"
$DownloadRoot = Join-Path $env:USERPROFILE "Downloads\YTD Studio Downloads"
$TaskName = "YTD Studio"
$Port = 8501
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

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
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $candidatePaths = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe")
    )

    foreach ($path in $candidatePaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

if (-not (Test-Administrator)) {
    Write-Host "Please run this setup from an Administrator PowerShell or Terminal." -ForegroundColor Red
    Write-Host "Example:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 1
}

Write-Step "Checking UV"
$UvPath = Get-UvCommand
if (-not $UvPath) {
    Write-Host "UV was not found. Installing UV with Astral's official Windows installer..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
    $UvPath = Get-UvCommand
}

if (-not $UvPath) {
    throw "UV installation finished, but uv.exe was not found. Close this terminal, open a new Administrator terminal, and run setup again."
}
Write-Host "Using UV: $UvPath" -ForegroundColor Green

Write-Step "Creating folders"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DownloadRoot "video") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DownloadRoot "audio") | Out-Null

Write-Step "Copying app files to $InstallDir"
$excludeDirs = @(".git", ".venv", "__pycache__", "downloads", ".codex-remote-attachments")
$excludeFiles = @("*.pyc", "*.pyo", ".DS_Store", "download-history.json")
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

$robocopyLine = "robocopy " + ($robocopyArgs -join " ")
cmd /c $robocopyLine | Out-Host
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

Write-Step "Writing startup launcher"
$LauncherPath = Join-Path $InstallDir "Start-YTD-Studio.ps1"
$HiddenLauncherPath = Join-Path $InstallDir "Start-YTD-Studio-Hidden.vbs"
$LinksPath = Join-Path $InstallDir "Show-YTD-Studio-Links.ps1"
$LogPath = Join-Path $InstallDir "ytd-studio.log"
$LinksScript = @"
`$ErrorActionPreference = "Stop"
`$Port = $Port
`$Desktop = [Environment]::GetFolderPath("Desktop")
`$LocalUrl = "http://localhost:`$Port"
`$HostUrl = "http://`$(`$env:COMPUTERNAME):`$Port"
`$IpAddresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        `$_.IPAddress -notlike "127.*" -and
        `$_.IPAddress -notlike "169.254.*" -and
        `$_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object InterfaceMetric, InterfaceIndex |
    Select-Object -ExpandProperty IPAddress -Unique

`$NetworkUrls = @()
foreach (`$Ip in `$IpAddresses) {
    `$NetworkUrls += "http://`$(`$Ip):`$Port"
}

`$Lines = @(
    "YTD Studio links",
    "",
    "This computer:",
    "  `$LocalUrl",
    "",
    "Try this from another device on the same Wi-Fi first:",
    "  `$HostUrl",
    ""
)

if (`$NetworkUrls.Count -gt 0) {
    `$Lines += "Current network IP links:"
    foreach (`$Url in `$NetworkUrls) {
        `$Lines += "  `$Url"
    }
}
else {
    `$Lines += "Current network IP links:"
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

Write-Host ""
`$Lines | ForEach-Object { Write-Host `$_ }
Write-Host ""
Write-Host "Saved links to: `$OutputFile" -ForegroundColor Green
"@
Set-Content -Path $LinksPath -Value $LinksScript -Encoding UTF8

$Launcher = @"
`$ErrorActionPreference = "Stop"
`$AppDir = "C:\YTD Studio"
`$UvExe = "$UvPath"
`$Port = $Port
`$Url = "http://localhost:`$Port"
`$LogPath = "$LogPath"

function Write-Log {
    param([string]`$Message)
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "`$timestamp  `$Message" | Add-Content -Path `$LogPath -Encoding UTF8
}

try {
    Set-Location `$AppDir

    & "$LinksPath" *> `$null

    `$listener = Get-NetTCPConnection -LocalPort `$Port -State Listen -ErrorAction SilentlyContinue
    if (`$listener) {
        Write-Log "Port `$Port is already listening. Startup skipped."
        exit 0
    }

    Write-Log "Starting YTD Studio on http://localhost:`$Port"
    `$env:PATH = "`$env:USERPROFILE\.local\bin;`$env:USERPROFILE\.cargo\bin;`$env:PATH"
    & `$UvExe run streamlit run app.py --server.headless=true --server.address=0.0.0.0 --server.port=`$Port --browser.gatherUsageStats=false --server.fileWatcherType=none *>> `$LogPath
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
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""$LauncherPath""", 0, False
"@
Set-Content -Path $HiddenLauncherPath -Value $HiddenLauncher -Encoding ASCII

Write-Step "Registering Windows startup task"
$Action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$HiddenLauncherPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
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
Start-Sleep -Seconds 4
& $LinksPath

Write-Host ""
Write-Host "YTD Studio setup complete." -ForegroundColor Green
Write-Host "Installed app: $InstallDir"
Write-Host "Downloads folder: $DownloadRoot"
Write-Host "Local URL: http://localhost:$Port"
Write-Host "Network links are saved on Desktop: YTD Studio Links.txt"
Write-Host "Refresh network links any time by running: $LinksPath"
Write-Host "Startup task: $TaskName"
Write-Host ""
Write-Host "Load the browser extension manually from:"
Write-Host "  $InstallDir\extension"
Write-Host ""
