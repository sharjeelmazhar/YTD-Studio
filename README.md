# YTD Studio

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue)
![Python](https://img.shields.io/badge/Python-managed%20by%20UV-green)
![UI](https://img.shields.io/badge/UI-Streamlit-ff4b4b)

YTD Studio is a local Windows web app for downloading YouTube content as MP4
video or MP3 audio. It runs on the user's own computer, opens in a browser, and
saves downloads to the Windows Downloads folder.

Only download content you own, have permission to download, or are legally
allowed to save.

## Table Of Contents

- [Features](#features)
- [Install On Windows](#install-on-windows)
- [Open The App](#open-the-app)
- [Install The Browser Extension](#install-the-browser-extension)
- [Download Location](#download-location)
- [Mobile Access On The Same Network](#mobile-access-on-the-same-network)
- [Reset Or Uninstall](#reset-or-uninstall)
- [Manual Development Run](#manual-development-run)
- [Troubleshooting](#troubleshooting)

## Features

- Download MP4 video at `480p`, `720p`, or `1080p`
- Download MP3 audio from the best available YouTube audio stream
- Show download progress with percentage, speed, ETA, downloaded size, and total size
- Save audio and video into separate folders
- Resume partial downloads when YouTube and `yt-dlp` allow it
- Track lifetime downloaded data locally
- Start automatically when Windows logs in
- Optional Brave/Chrome extension with quick YouTube page buttons
- Uses UV for Python and dependency management
- Uses bundled ffmpeg from `imageio-ffmpeg`

## Install On Windows

Use Windows 10 or Windows 11.

1. Download this repository as a ZIP or clone it.
2. Extract the project folder.
3. Open PowerShell or Windows Terminal as Administrator in the project folder.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Setup-YTD-Studio.ps1"
```

The setup script will:

- install UV if it is missing
- copy the app to `C:\YTD Studio`
- create `%USERPROFILE%\Downloads\YTD Studio Downloads\video`
- create `%USERPROFILE%\Downloads\YTD Studio Downloads\audio`
- run `uv sync`
- create a hidden Windows startup task named `YTD Studio`
- start the app on `http://localhost:8501`
- create `YTD Studio.url` and `YTD Studio Links.txt` on the Desktop

The app starts automatically on future Windows logins.

## Open The App

On the Windows computer running YTD Studio, open:

```text
http://localhost:8501
```

The setup script also creates a Desktop shortcut named:

```text
YTD Studio.url
```

## Install The Browser Extension

The extension is optional. It adds compact download buttons to YouTube watch
pages.

After setup:

1. Open `brave://extensions` or `chrome://extensions`
2. Turn on Developer mode
3. Click Load unpacked
4. Select:

```text
C:\YTD Studio\extension
```

The extension adds quick buttons for:

```text
720p video
MP3 audio
```

The extension expects the local app to be running at:

```text
http://localhost:8501
```

## Download Location

Downloads are saved here:

```text
%USERPROFILE%\Downloads\YTD Studio Downloads
```

Inside that folder:

```text
audio\
video\
```

The lifetime usage file is stored here:

```text
C:\YTD Studio\download-history.json
```

That file records completed downloads and total downloaded bytes. Deleting the
Windows download folder does not reset this lifetime total.

## Mobile Access On The Same Network

The startup task runs Streamlit on `0.0.0.0:8501`, so other devices on the same
Wi-Fi or LAN can open the app from the Windows computer.

### Quick IP Command

Run this in PowerShell on the Windows computer:

```powershell
$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | Select-Object -First 1 -ExpandProperty IPv4Address).IPAddress; "Open this on another device: http://$ip`:8501"
```

Example output:

```text
Open this on another device: http://192.168.1.5:8501
```

Open that URL on a phone, tablet, or laptop connected to the same Wi-Fi.

You can also check manually with:

```powershell
ipconfig
```

Look for the active Wi-Fi or Ethernet adapter, then copy the `IPv4 Address`.
For example, if the IPv4 address is `192.168.1.5`, open:

```text
http://192.168.1.5:8501
```

After setup, open this Desktop file:

```text
YTD Studio Links.txt
```

It includes:

- `http://localhost:8501` for the Windows computer
- `http://COMPUTER-NAME:8501` when the network supports computer names
- `http://192.168.x.x:8501` style links for the current network

If the computer switches Wi-Fi networks, refresh the link file:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\YTD Studio\Show-YTD-Studio-Links.ps1"
```

Downloads still save on the Windows computer, even when started from a phone or
another laptop.

## Reset Or Uninstall

Run this from an Administrator PowerShell or Windows Terminal:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Reset-YTD-Studio.ps1"
```

Reset removes:

- `C:\YTD Studio`
- `%USERPROFILE%\Downloads\YTD Studio Downloads`
- the Windows startup task
- Desktop shortcut/link files
- UV installed in the current user profile

To keep UV installed:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Reset-YTD-Studio.ps1" -KeepUv
```

If Brave or Chrome still shows the unpacked extension, remove it manually from
the browser extensions page.

## Manual Development Run

For local testing without installing to `C:\YTD Studio`:

```powershell
uv sync
uv run streamlit run app.py --server.address=localhost --server.port=8501
```

Or double-click:

```text
Start YouTube Downloader.bat
```

## Troubleshooting

If `http://localhost:8501` does not open:

1. Open Task Scheduler and check the `YTD Studio` task.
2. Check the log file:

```text
C:\YTD Studio\ytd-studio.log
```

3. Restart the task:

```powershell
Start-ScheduledTask -TaskName "YTD Studio"
```

If port `8501` is already used by another app, stop that app or change the port
inside `Setup-YTD-Studio.ps1` before installing.

If downloads fail, update dependencies:

```powershell
cd "C:\YTD Studio"
uv sync
```

Then restart the app or restart Windows.
