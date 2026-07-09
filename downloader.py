from __future__ import annotations

import json
import os
import re
import shutil
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

import imageio_ffmpeg
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


APP_DIR = Path(__file__).resolve().parent
WINDOWS_DOWNLOADS_DIR = Path.home() / "Downloads"
OUTPUT_DIR = WINDOWS_DOWNLOADS_DIR / "YTD Studio Downloads"
VIDEO_DIR = OUTPUT_DIR / "video"
AUDIO_DIR = OUTPUT_DIR / "audio"
HISTORY_FILE = APP_DIR / "download-history.json"
NETWORK_ERROR_WORDS = (
    "network is unreachable",
    "no internet",
    "temporary failure in name resolution",
    "name resolution",
    "failed to resolve",
    "getaddrinfo failed",
    "connection reset",
    "connection aborted",
    "connection refused",
    "connection timed out",
    "timed out",
    "timeout",
    "ssl",
    "remote end closed connection",
    "unable to download webpage",
    "http error 5",
    "http error 403",
    "http error 429",
)
ANSI_RE = re.compile(r"(?:\x1b|\ufffd)\[[0-?]*[ -/]*[@-~]")

ProgressCallback = Callable[[dict], None]
QUALITY_OPTIONS = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}
MEDIA_MODES = {"video", "audio"}
YOUTUBE_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{11})\]")


@dataclass
class DownloadResult:
    ok: bool
    message: str
    files: list[Path] = field(default_factory=list)
    details: str = ""


def detected_workers() -> int:
    return max(1, os.cpu_count() or 1)


def empty_download_history() -> dict:
    return {
        "schema_version": 1,
        "total_bytes": 0,
        "downloads": [],
    }


def read_download_history(path: Path = HISTORY_FILE) -> dict:
    if not path.exists():
        return empty_download_history()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_download_history()

    if not isinstance(data, dict):
        return empty_download_history()
    downloads = data.get("downloads")
    if not isinstance(downloads, list):
        downloads = []
    try:
        total_bytes = int(data.get("total_bytes", 0))
    except (TypeError, ValueError):
        total_bytes = 0
    if total_bytes < 0:
        total_bytes = 0
    return {
        "schema_version": 1,
        "total_bytes": total_bytes,
        "downloads": downloads,
    }


def write_download_history(data: dict, path: Path = HISTORY_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp_path.replace(path)


def file_size_bytes(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def record_download_history(
    files: list[Path],
    url: str,
    media_mode: str,
    quality: str | int | None,
    path: Path = HISTORY_FILE,
) -> None:
    entries = []
    for file in files:
        size_bytes = file_size_bytes(file)
        if size_bytes <= 0:
            continue
        entries.append(
            {
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "mode": normalize_media_mode(media_mode),
                "quality": str(quality or ""),
                "video_id": extract_video_id(file.name) or extract_video_id(url) or "",
                "file_name": file.name,
                "file_path": str(file),
                "size_bytes": size_bytes,
            }
        )

    if not entries:
        return

    history = read_download_history(path)
    history["downloads"].extend(entries)
    history["total_bytes"] = int(history.get("total_bytes", 0)) + sum(
        entry["size_bytes"] for entry in entries
    )
    write_download_history(history, path)


def format_total_downloaded_gb(total_bytes: int | float) -> str:
    try:
        value = max(0.0, float(total_bytes))
    except (TypeError, ValueError):
        value = 0.0
    gb = value / (1024 ** 3)
    return f"{gb:,.1f} GB"


def normalize_quality(quality: str | int | None) -> int:
    if quality is None:
        return 720
    if isinstance(quality, int):
        return quality if quality in QUALITY_OPTIONS.values() else 720

    cleaned = quality.strip().lower()
    if cleaned in QUALITY_OPTIONS:
        return QUALITY_OPTIONS[cleaned]
    if cleaned.endswith("p") and cleaned[:-1].isdigit():
        value = int(cleaned[:-1])
        return value if value in QUALITY_OPTIONS.values() else 720
    if cleaned.isdigit():
        value = int(cleaned)
        return value if value in QUALITY_OPTIONS.values() else 720
    return 720


def normalize_media_mode(mode: str | None) -> str:
    cleaned = (mode or "video").strip().lower()
    return cleaned if cleaned in MEDIA_MODES else "video"


def output_dir_for_mode(mode: str | None) -> Path:
    return AUDIO_DIR if normalize_media_mode(mode) == "audio" else VIDEO_DIR


def has_internet(timeout: float = 3.0) -> bool:
    try:
        socket.create_connection(("www.youtube.com", 443), timeout=timeout).close()
    except OSError:
        return False
    return True


def looks_like_youtube_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    return parsed.scheme in {"http", "https"} and (
        host.endswith("youtube.com") or host.endswith("youtu.be")
    )


def extract_video_id(value: str) -> str | None:
    text = value.strip()
    bracket_match = YOUTUBE_ID_RE.search(text)
    if bracket_match:
        return bracket_match.group(1)

    parsed = urlparse(text)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
        return video_id if len(video_id) == 11 else None

    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            return video_id if len(video_id) == 11 else None
        for prefix in ("/shorts/", "/embed/", "/live/"):
            if parsed.path.startswith(prefix):
                video_id = parsed.path.removeprefix(prefix).split("/")[0]
                return video_id if len(video_id) == 11 else None
    return None


def thumbnail_url(video_id: str | None) -> str:
    if not video_id:
        return ""
    return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"


def download_search_dirs(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    dirs = [output_dir, output_dir / "video", output_dir / "audio"]
    return [folder for folder in dirs if folder.exists()]


def find_existing_downloads(
    video_id: str | None,
    output_dir: Path = OUTPUT_DIR,
    media_mode: str | None = None,
) -> list[Path]:
    if not video_id or not output_dir.exists():
        return []
    mode = normalize_media_mode(media_mode) if media_mode else None
    if mode == "audio":
        media_exts = {".mp3"}
        allowed_folder_names = {"audio"}
    elif mode == "video":
        media_exts = {".mp4", ".mkv", ".webm", ".mov"}
        allowed_folder_names = {"video"}
    else:
        media_exts = {".mp4", ".mkv", ".webm", ".mov", ".mp3"}
        allowed_folder_names = {"audio", "video"}

    matches: list[Path] = []
    for folder in download_search_dirs(output_dir):
        if mode and folder != output_dir and folder.name not in allowed_folder_names:
            continue
        matches.extend(
            path
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in media_exts
            and f"[{video_id}]" in path.name
        )
    return sorted(
        matches,
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def is_network_error(message: str) -> bool:
    text = message.lower()
    return any(word in text for word in NETWORK_ERROR_WORDS)


def clean_terminal_text(value: object, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = ANSI_RE.sub("", str(value))
    text = text.replace("\x1b", "").replace("\ufffd", "")
    text = "".join(char for char in text if char.isprintable())
    text = " ".join(text.split())
    return text.strip() or fallback


def format_bytes_per_second(value: object) -> str:
    try:
        speed = float(value or 0)
    except (TypeError, ValueError):
        return "calculating speed"
    if speed <= 0:
        return "calculating speed"

    units = ["B/s", "KiB/s", "MiB/s", "GiB/s"]
    unit_index = 0
    while speed >= 1024 and unit_index < len(units) - 1:
        speed /= 1024
        unit_index += 1
    return f"{speed:.2f} {units[unit_index]}"


def format_file_size(value: object) -> str:
    try:
        size = float(value or 0)
    except (TypeError, ValueError):
        return "unknown size"
    if size <= 0:
        return "unknown size"

    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{size:.0f} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def format_eta(value: object) -> str:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if seconds < 0:
        return "unknown"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def friendly_error(exc: Exception) -> str:
    message = str(exc).strip()
    if is_network_error(message):
        return (
            "The internet connection looks unavailable or unstable. "
            "Reconnect and try again; the app will resume partial downloads when possible."
        )
    if "ffmpeg" in message.lower():
        return "ffmpeg is required to merge video and audio. Install ffmpeg and try again."
    if "private video" in message.lower():
        return "This video is private, so it cannot be downloaded."
    if "video unavailable" in message.lower():
        return "This video is unavailable from YouTube."
    if "sign in" in message.lower() or "age" in message.lower():
        return "YouTube requires sign-in or age verification for this video."
    return "The download failed. Check the link and try again."


def progress_values(info: dict) -> dict:
    total = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
    downloaded = info.get("downloaded_bytes") or 0
    percent = 0.0
    if total:
        percent = min(1.0, max(0.0, downloaded / total))

    return {
        "status": info.get("status", ""),
        "percent": percent,
        "percent_text": f"{percent * 100:.1f}%" if total else clean_terminal_text(info.get("_percent_str"), "0.0%"),
        "speed": format_bytes_per_second(info.get("speed")),
        "eta": format_eta(info.get("eta")),
        "downloaded": format_file_size(downloaded),
        "total": format_file_size(total),
        "filename": clean_terminal_text(info.get("filename")),
    }


class YtdlpLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, message: str) -> None:
        if message.startswith("[debug]"):
            self.messages.append(message)

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warning(self, message: str) -> None:
        self.messages.append(f"Warning: {message}")

    def error(self, message: str) -> None:
        self.messages.append(f"Error: {message}")


def build_ydl_options(
    workers: int,
    quality: str | int | None = 720,
    output_dir: Path = VIDEO_DIR,
    media_mode: str = "video",
    progress_callback: ProgressCallback | None = None,
    logger: YtdlpLogger | None = None,
) -> dict:
    def hook(info: dict) -> None:
        if progress_callback:
            progress_callback(progress_values(info))

    height = normalize_quality(quality)
    mode = normalize_media_mode(media_mode)
    if mode == "audio":
        ytdlp_format = "bestaudio[ext=m4a]/bestaudio/best"
        format_sort = ["abr", "asr", "ext:m4a"]
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            },
            {"key": "FFmpegMetadata"},
        ]
        postprocessor_args = {"ExtractAudio": ["-threads", str(max(1, workers))]}
    else:
        ytdlp_format = (
            f"bv*[height={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height={height}]+ba/"
            f"bv*[height<={height}]+ba/"
            f"best[height={height}]/best[height<={height}]"
        )
        format_sort = [f"res:{height}", "ext:mp4:m4a", "vcodec:h264", "acodec:aac"]
        postprocessors = []
        postprocessor_args = {"Merger": ["-threads", str(max(1, workers))]}

    options = {
        "format": ytdlp_format,
        "format_sort": format_sort,
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).200B [%(id)s].%(ext)s"),
        "paths": {"home": str(output_dir)},
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "concurrent_fragment_downloads": max(1, workers),
        "continuedl": True,
        "retries": 50,
        "fragment_retries": 50,
        "file_access_retries": 20,
        "extractor_retries": 10,
        "socket_timeout": 120,
        "retry_sleep_functions": {
            "http": lambda attempt: min(60, 2 * attempt),
            "fragment": lambda attempt: min(60, 2 * attempt),
            "file_access": lambda attempt: min(30, attempt),
        },
        "noplaylist": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "color": "no_color",
        "logger": logger,
        "postprocessors": postprocessors,
        "postprocessor_args": postprocessor_args,
        "progress_hooks": [hook],
    }

    aria2c = shutil.which("aria2c")
    if aria2c:
        options["external_downloader"] = {"default": aria2c}
        options["external_downloader_args"] = {
            "default": [
                "-x",
                str(max(1, workers)),
                "-s",
                str(max(1, workers)),
                "-k",
                "1M",
                "--timeout=120",
                "--connect-timeout=120",
                "--max-tries=50",
                "--retry-wait=5",
                "--file-allocation=none",
                "--summary-interval=0",
            ]
        }

    return options


def newest_media_files(output_dir: Path, since: float, media_mode: str | None = None) -> list[Path]:
    if not output_dir.exists():
        return []
    mode = normalize_media_mode(media_mode) if media_mode else None
    if mode == "audio":
        media_exts = {".mp3"}
    elif mode == "video":
        media_exts = {".mp4", ".mkv", ".webm", ".mov"}
    else:
        media_exts = {".mp4", ".mkv", ".webm", ".mov", ".mp3"}
    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in media_exts
        and path.stat().st_mtime >= since
    ]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def cleanup_audio_source_files(output_dir: Path, video_id: str | None, since: float) -> None:
    if not video_id or not output_dir.exists():
        return
    for path in output_dir.iterdir():
        if (
            path.is_file()
            and path.suffix.lower() in {".m4a", ".opus", ".webm"}
            and f"[{video_id}]" in path.name
            and path.stat().st_mtime >= since
        ):
            try:
                path.unlink()
            except OSError:
                pass


def download_media(
    url: str,
    workers: int | None = None,
    quality: str | int | None = 720,
    media_mode: str = "video",
    output_dir: Path | None = None,
    progress_callback: ProgressCallback | None = None,
    check_connection: bool = True,
    allow_redownload: bool = True,
) -> DownloadResult:
    mode = normalize_media_mode(media_mode)
    target_dir = output_dir or output_dir_for_mode(mode)
    cleaned_url = url.strip()
    if not cleaned_url:
        return DownloadResult(False, "Paste a YouTube link first.")

    if not looks_like_youtube_url(cleaned_url):
        return DownloadResult(False, "That does not look like a YouTube link.")

    video_id = extract_video_id(cleaned_url)
    existing_files = find_existing_downloads(video_id, OUTPUT_DIR, media_mode=mode)
    if existing_files and not allow_redownload:
        return DownloadResult(
            False,
            "This video is already in your downloads folder. Enable re-download if you want another copy.",
            files=existing_files,
        )

    if check_connection and not has_internet():
        return DownloadResult(
            False,
            "No internet connection detected. Connect to the internet and try again.",
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    started_at = __import__("time").time()
    logger = YtdlpLogger()

    try:
        with YoutubeDL(
            build_ydl_options(
                workers=workers or detected_workers(),
                quality=quality,
                output_dir=target_dir,
                media_mode=mode,
                progress_callback=progress_callback,
                logger=logger,
            )
        ) as ydl:
            ydl.download([cleaned_url])
    except DownloadError as exc:
        return DownloadResult(False, friendly_error(exc), details=str(exc))
    except OSError as exc:
        return DownloadResult(False, friendly_error(exc), details=str(exc))
    except KeyboardInterrupt:
        return DownloadResult(False, "Download cancelled.", details="KeyboardInterrupt")

    if mode == "audio":
        cleanup_audio_source_files(target_dir, video_id, started_at)

    files = newest_media_files(target_dir, started_at, mode)
    if files:
        record_download_history(files, cleaned_url, mode, quality)
        return DownloadResult(True, "Download complete.", files=files)
    return DownloadResult(True, "Download complete. Check the downloads folder.")


def download_video(
    url: str,
    workers: int | None = None,
    quality: str | int | None = 720,
    output_dir: Path | None = None,
    progress_callback: ProgressCallback | None = None,
    check_connection: bool = True,
    allow_redownload: bool = True,
) -> DownloadResult:
    return download_media(
        url=url,
        workers=workers,
        quality=quality,
        media_mode="video",
        output_dir=output_dir,
        progress_callback=progress_callback,
        check_connection=check_connection,
        allow_redownload=allow_redownload,
    )
