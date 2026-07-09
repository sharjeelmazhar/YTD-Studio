from __future__ import annotations

import argparse

from downloader import detected_workers, download_media, output_dir_for_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fast 720p YouTube downloader for Windows, powered by yt-dlp."
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=detected_workers(),
        help="parallel fragment workers; default uses all detected CPU cores",
    )
    parser.add_argument(
        "-q",
        "--quality",
        choices=["480p", "720p", "1080p"],
        default="720p",
        help="maximum video quality to download",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["video", "audio"],
        default="video",
        help="download MP4 video or MP3 audio",
    )
    return parser.parse_args()


def terminal_progress(info: dict) -> None:
    if info["status"] == "downloading":
        percent = info["percent_text"] or f"{info['percent'] * 100:.1f}%"
        speed = info["speed"] or "?/s"
        eta = info["eta"] or "?"
        print(f"\rDownloading: {percent} at {speed} ETA {eta}", end="", flush=True)
    elif info["status"] == "finished":
        print("\nDownload finished. Merging video and audio if needed...")


def main() -> int:
    args = parse_args()
    url = args.url or input("YouTube URL: ").strip()

    print(f"Saving to: {output_dir_for_mode(args.mode)}")
    print(f"Mode: {args.mode}")
    if args.mode == "video":
        print(f"Target quality: {args.quality}")
    else:
        print("Target audio: best available audio, converted to MP3")
    print(f"Parallel workers: {max(1, args.workers)}")

    result = download_media(
        url,
        workers=args.workers,
        quality=args.quality,
        media_mode=args.mode,
        progress_callback=terminal_progress,
    )
    if not result.ok:
        print(f"\n{result.message}")
        if result.details:
            print(result.details)
        return 2

    print(f"\n{result.message}")
    for file in result.files:
        print(file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
