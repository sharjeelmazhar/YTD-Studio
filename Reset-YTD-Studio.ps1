#Requires -Version 5.1

param(
    [switch]$KeepUv
)

$ErrorActionPreference = "Stop"

$InstallDir = "C:\YTD Studio"
$DownloadRoot = Join-Path $env:USERPROFILE "Downloads\YTD Studio Downloads"
$TaskName = "YTD Studio"
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

function Remove-IfExists {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
        Write-Host "Removed: $Path"
    }
}

function Test-IsInsidePath {
    param(
        [string]$ChildPath,
        [string]$ParentPath
    )

    if ([string]::IsNullOrWhiteSpace($ChildPath) -or [string]::IsNullOrWhiteSpace($ParentPath)) {
        return $false
    }

    $child = [IO.Path]::GetFullPath($ChildPath).TrimEnd('\')
    $parent = [IO.Path]::GetFullPath($ParentPath).TrimEnd('\')
    return $child.Equals($parent, [StringComparison]::OrdinalIgnoreCase) -or
        $child.StartsWith("$parent\", [StringComparison]::OrdinalIgnoreCase)
}

if (-not (Test-Administrator)) {
    Write-Host "Please run this reset from an Administrator PowerShell or Terminal." -ForegroundColor Red
    Write-Host "Example:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 1
}

$currentDir = (Get-Location).ProviderPath
$scriptPath = $PSCommandPath
$isRunningFromInstallDir =
    (Test-IsInsidePath -ChildPath $currentDir -ParentPath $InstallDir) -or
    (Test-IsInsidePath -ChildPath $scriptPath -ParentPath $InstallDir)

if ($isRunningFromInstallDir) {
    $tempScript = Join-Path $env:TEMP "Reset-YTD-Studio.ps1"
    Copy-Item -LiteralPath $PSCommandPath -Destination $tempScript -Force

    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$tempScript`""
    )
    if ($KeepUv) {
        $arguments += "-KeepUv"
    }

    Write-Host "Reset was started from inside $InstallDir, so it will relaunch from TEMP first." -ForegroundColor Yellow
    Write-Host "Continuing from: $tempScript"
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $env:TEMP -Wait -PassThru
    exit $process.ExitCode
}

Write-Host "This will remove YTD Studio app files, downloads, startup task, Desktop URL shortcut, and UV unless -KeepUv is used." -ForegroundColor Yellow
Write-Host "Press Ctrl+C now if you want to stop."
Start-Sleep -Seconds 3

Write-Step "Stopping YTD Studio processes"
Get-CimInstance Win32_Process |
    Where-Object {
        ($_.CommandLine -like "*C:\YTD Studio*") -or
        ($_.CommandLine -like "*streamlit run app.py*")
    } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped process $($_.ProcessId): $($_.Name)"
        }
        catch {
            Write-Host "Could not stop process $($_.ProcessId): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }

Write-Step "Removing Windows startup task"
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed task: $TaskName"
}

Write-Step "Removing files and folders"
Remove-IfExists $InstallDir
Remove-IfExists $DownloadRoot
Remove-IfExists (Join-Path $Desktop "YTD Studio.url")
Remove-IfExists (Join-Path $Desktop "YTD Studio Links.txt")

if (-not $KeepUv) {
    Write-Step "Removing UV"
    $uvFiles = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".local\bin\uvx.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uvx.exe")
    )
    foreach ($file in $uvFiles) {
        if (Test-Path -LiteralPath $file) {
            Remove-Item -LiteralPath $file -Force
            Write-Host "Removed: $file"
        }
    }

    $uvDirs = @(
        (Join-Path $env:LOCALAPPDATA "uv"),
        (Join-Path $env:APPDATA "uv"),
        (Join-Path $env:USERPROFILE ".cache\uv")
    )
    foreach ($dir in $uvDirs) {
        Remove-IfExists $dir
    }
}
else {
    Write-Host "Keeping UV because -KeepUv was used."
}

Write-Host ""
Write-Host "YTD Studio reset complete." -ForegroundColor Green
Write-Host "If Brave still shows the old unpacked extension, remove it manually from brave://extensions."
