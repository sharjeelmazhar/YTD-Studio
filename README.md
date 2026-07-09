# YTD Studio

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue)
![Python](https://img.shields.io/badge/Python-managed%20by%20UV-green)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b)

YTD Studio is a private Windows web app for downloading YouTube videos as MP4 or
audio as MP3. It runs locally in your browser, saves files to your Windows
Downloads folder, and can add compact download buttons to YouTube through a
local Brave/Chrome extension.

Only download videos you own, have permission to download, or are allowed to
save.

## Table Of Contents

- [Features](#features)
- [Upload This Project To GitHub](#upload-this-project-to-github)
- [Set Up A New Computer](#set-up-a-new-computer)
- [Install The YouTube Extension](#install-the-youtube-extension)
- [Download Location](#download-location)
- [Reset A Test Computer](#reset-a-test-computer)
- [Manual Start](#manual-start)
- [Mobile Access On Same Wi-Fi](#mobile-access-on-same-wi-fi)

## Features

- Downloads MP4 video at `480p`, `720p`, or `1080p`
- Downloads MP3 audio from the best available YouTube audio
- Uses a bundled ffmpeg dependency for MP4 merging and MP3 conversion
- Uses UV for Python and dependency management
- Saves downloads to `%USERPROFILE%\Downloads\YTD Studio Downloads`
- Creates separate `audio` and `video` folders
- Resumes partial downloads when YouTube allows it
- Starts automatically when Windows logs in
- Provides a local Brave/Chrome extension with quick YouTube buttons
- Tracks lifetime downloaded data in `C:\YTD Studio\download-history.json`

## Upload This Project To GitHub

### Recommended: Use GitHub Desktop Or Git

Using GitHub Desktop or Git is the easiest way to upload the whole project,
including the `extension` folder. `.gitignore` will protect local folders such as
`.venv`, `__pycache__`, and `downloads`.

With GitHub Desktop:

1. Install GitHub Desktop.
2. Sign in.
3. Add this local folder as a repository.
4. Publish it to GitHub.

With Git in a terminal:

```powershell
git init
git add .
git commit -m "Initial YTD Studio upload"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YTD-Studio.git
git push -u origin main
```

### Browser Upload

If you upload through the GitHub website, `.gitignore` does not automatically
stop files you manually select. You must avoid selecting local generated folders.

Upload these files and folders:

```text
app.py
downloader.py
main.py
test_downloader.py
pyproject.toml
uv.lock
.python-version
.gitignore
README.md
Setup-YTD-Studio.ps1
Reset-YTD-Studio.ps1
Start YouTube Downloader.bat
extension/
```

Do not upload these:

```text
.venv/
__pycache__/
downloads/
shareable.zip
ytd-studio.log
.streamlit/
.codex-remote-attachments/
```

If the browser uploader does not include the `extension` folder, create these
two files manually in GitHub:

```text
extension/manifest.json
extension/youtube-button.js
```

GitHub creates the `extension` folder automatically when files exist inside it.

## Set Up A New Computer

> [!IMPORTANT]
> Use this section on a fresh Windows 10 or Windows 11 computer.

1. Download this repository from GitHub as a ZIP.
2. Extract the ZIP.
3. Open PowerShell or Windows Terminal as Administrator in the extracted folder.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Setup-YTD-Studio.ps1"
```

The setup script:

- installs UV if it is missing
- copies the app to `C:\YTD Studio`
- creates `%USERPROFILE%\Downloads\YTD Studio Downloads\video`
- creates `%USERPROFILE%\Downloads\YTD Studio Downloads\audio`
- runs `uv sync`
- creates a Windows startup task named `YTD Studio`
- starts the app immediately at `http://localhost:8501`
- creates `YTD Studio Links.txt` on the Desktop with current phone/network URLs

The app starts automatically on future Windows logins. The browser extension is
the only manual step.

## Install The YouTube Extension

After setup, load the extension manually in Brave or Chrome:

1. Open `brave://extensions` or `chrome://extensions`
2. Turn on Developer mode
3. Click Load unpacked
4. Select:

```text
C:\YTD Studio\extension
```

YouTube watch pages will show:

```text
🎬 720p video
🎵 MP3 audio
```

The extension uses `http://localhost:8501`, so keep the app on port `8501`.

## Download Location

Files are saved here:

```text
%USERPROFILE%\Downloads\YTD Studio Downloads
```

Inside:

```text
audio\
video\
```

YTD Studio also keeps a lifetime usage file here:

```text
C:\YTD Studio\download-history.json
```

That file stores each successful download entry and total downloaded bytes. It
does not depend on the Windows Downloads folder, so deleting downloaded files
does not reset the app's lifetime total.

## Reset A Test Computer

> [!WARNING]
> This removes the installed app, downloaded files, startup task, and UV unless
> you use `-KeepUv`.

To remove the app and test setup again from a clean state, run as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Reset-YTD-Studio.ps1"
```

This removes:

- `C:\YTD Studio`
- `%USERPROFILE%\Downloads\YTD Studio Downloads`
- the Windows startup task
- the Desktop app URL shortcut and network links text file
- UV installed in the current user profile

To keep UV:

```powershell
powershell -ExecutionPolicy Bypass -File ".\Reset-YTD-Studio.ps1" -KeepUv
```

If Brave or Chrome still shows the unpacked extension, remove it manually from
the browser extensions page.

## Manual Start

For testing without installing:

```powershell
uv run streamlit run app.py --server.address=localhost --server.port=8501
```

Or double-click:

```text
Start YouTube Downloader.bat
```

## Mobile Access On Same Wi-Fi

The startup task runs the app on `0.0.0.0:8501`, so phones and laptops on the
same Wi-Fi can open it from this computer.

After setup, check this Desktop file:

```text
YTD Studio Links.txt
```

It contains the current URLs, including:

- `http://localhost:8501` for this computer
- `http://COMPUTER-NAME:8501` for other devices, when your network supports it
- `http://192.168.x.x:8501` style IP links for the current Wi-Fi/Ethernet network

If you switch Wi-Fi networks, refresh the file by running:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\YTD Studio\Show-YTD-Studio-Links.ps1"
```

Downloads still save on the Windows computer.
