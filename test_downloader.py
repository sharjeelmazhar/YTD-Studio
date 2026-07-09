from __future__ import annotations

import unittest

from downloader import (
    build_ydl_options,
    clean_terminal_text,
    cleanup_audio_source_files,
    extract_video_id,
    find_existing_downloads,
    format_file_size,
    format_total_downloaded_gb,
    format_bytes_per_second,
    format_eta,
    is_network_error,
    looks_like_youtube_url,
    normalize_quality,
    newest_media_files,
    output_dir_for_mode,
    progress_values,
    read_download_history,
    record_download_history,
)
from pathlib import Path
from tempfile import TemporaryDirectory


class DownloaderTests(unittest.TestCase):
    def test_accepts_youtube_urls(self) -> None:
        self.assertTrue(looks_like_youtube_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(looks_like_youtube_url("https://youtu.be/abc"))

    def test_extracts_video_ids(self) -> None:
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=BaW_jenozKc"), "BaW_jenozKc")
        self.assertEqual(extract_video_id("https://youtu.be/BaW_jenozKc"), "BaW_jenozKc")
        self.assertEqual(extract_video_id("Some title [BaW_jenozKc].mp4"), "BaW_jenozKc")

    def test_rejects_non_youtube_urls(self) -> None:
        self.assertFalse(looks_like_youtube_url("https://example.com/watch?v=abc"))
        self.assertFalse(looks_like_youtube_url("not a url"))

    def test_network_error_detection(self) -> None:
        self.assertTrue(is_network_error("Failed to resolve www.youtube.com"))
        self.assertTrue(is_network_error("Connection timed out during download"))
        self.assertFalse(is_network_error("This video is private"))

    def test_quality_normalization(self) -> None:
        self.assertEqual(normalize_quality("480p"), 480)
        self.assertEqual(normalize_quality("1080"), 1080)
        self.assertEqual(normalize_quality("bad"), 720)

    def test_slow_connection_options(self) -> None:
        options = build_ydl_options(workers=2, quality="1080p")
        self.assertIn("1080", options["format"])
        self.assertTrue(options["continuedl"])
        self.assertEqual(options["socket_timeout"], 120)
        self.assertEqual(options["fragment_retries"], 50)

    def test_audio_options_extract_mp3(self) -> None:
        options = build_ydl_options(workers=2, media_mode="audio")
        self.assertIn("bestaudio", options["format"])
        self.assertEqual(options["postprocessors"][0]["preferredcodec"], "mp3")
        self.assertEqual(options["postprocessors"][0]["preferredquality"], "320")
        self.assertEqual(output_dir_for_mode("audio").name, "audio")
        self.assertEqual(output_dir_for_mode("video").name, "video")

    def test_progress_text_is_clean(self) -> None:
        self.assertEqual(clean_terminal_text("\x1b[0;94m16.1%\x1b[0m"), "16.1%")
        self.assertEqual(clean_terminal_text("�[0;32m6.24MiB/s�[0m"), "6.24MiB/s")
        self.assertEqual(format_bytes_per_second(1488978), "1.42 MiB/s")
        self.assertEqual(format_file_size(2 * 1024 * 1024 * 1024), "2.0 GiB")
        self.assertEqual(format_eta(54), "54s")

        progress = progress_values(
            {
                "status": "downloading",
                "downloaded_bytes": 161,
                "total_bytes": 1000,
                "speed": 1488978,
                "eta": 54,
                "_percent_str": "\x1b[0;94m16.1%\x1b[0m",
            }
        )
        self.assertEqual(progress["percent_text"], "16.1%")
        self.assertEqual(progress["speed"], "1.42 MiB/s")
        self.assertEqual(progress["downloaded"], "161 B")
        self.assertEqual(progress["total"], "1000 B")
        self.assertEqual(progress["eta"], "54s")

    def test_no_color_option_is_enabled(self) -> None:
        options = build_ydl_options(workers=2, quality="720p")
        self.assertTrue(options["no_color"])
        self.assertEqual(options["color"], "no_color")

    def test_finds_existing_downloads(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            matching = folder / "Video title [BaW_jenozKc].mp4"
            audio_dir = folder / "audio"
            audio_dir.mkdir()
            audio = audio_dir / "Video title [BaW_jenozKc].mp3"
            other = folder / "Other [11111111111].mp4"
            matching.write_bytes(b"video")
            audio.write_bytes(b"audio")
            other.write_bytes(b"video")
            self.assertEqual(set(find_existing_downloads("BaW_jenozKc", folder)), {matching, audio})
            self.assertEqual(find_existing_downloads("BaW_jenozKc", folder, media_mode="video"), [matching])
            self.assertEqual(find_existing_downloads("BaW_jenozKc", folder, media_mode="audio"), [audio])

    def test_audio_mode_ignores_and_cleans_source_audio(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            mp3 = folder / "Video title [BaW_jenozKc].mp3"
            m4a = folder / "Video title [BaW_jenozKc].m4a"
            mp3.write_bytes(b"mp3")
            m4a.write_bytes(b"source")

            self.assertEqual(find_existing_downloads("BaW_jenozKc", folder, media_mode="audio"), [mp3])
            self.assertEqual(newest_media_files(folder, 0, "audio"), [mp3])

            cleanup_audio_source_files(folder, "BaW_jenozKc", 0)
            self.assertTrue(mp3.exists())
            self.assertFalse(m4a.exists())

    def test_records_download_history(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            history = folder / "download-history.json"
            video = folder / "Video title [BaW_jenozKc].mp4"
            audio = folder / "Audio title [BaW_jenozKc].mp3"
            video.write_bytes(b"v" * 1024)
            audio.write_bytes(b"a" * 2048)

            record_download_history(
                [video],
                "https://www.youtube.com/watch?v=BaW_jenozKc",
                "video",
                "720p",
                history,
            )
            record_download_history(
                [audio],
                "https://www.youtube.com/watch?v=BaW_jenozKc",
                "audio",
                "best",
                history,
            )

            data = read_download_history(history)
            self.assertEqual(data["total_bytes"], 3072)
            self.assertEqual(len(data["downloads"]), 2)
            self.assertEqual(data["downloads"][0]["mode"], "video")
            self.assertEqual(data["downloads"][1]["mode"], "audio")

    def test_formats_total_downloaded_gb(self) -> None:
        self.assertEqual(format_total_downloaded_gb(0), "0.0 GB")
        self.assertEqual(format_total_downloaded_gb(1024 ** 3), "1.0 GB")
        self.assertEqual(format_total_downloaded_gb(int(1000.7 * (1024 ** 3))), "1,000.7 GB")


if __name__ == "__main__":
    unittest.main()
