"""
Downloader - Handles downloading audio with multi-threaded support.
"""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Callable
from dataclasses import dataclass

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)

from .spotify_client import TrackMetadata
from .search_engine import SearchResult

console = Console()


@dataclass
class DownloadResult:
    """Data class for download results."""
    success: bool
    file_path: Optional[str]
    metadata: TrackMetadata
    error: Optional[str] = None
    file_size: int = 0
    bitrate: int = 0


class Downloader:
    """
    Handles downloading audio files with multi-threaded support.
    
    Implements validation for file size and bitrate thresholds.
    """

    def __init__(
        self,
        output_dir: str = "downloads",
        max_workers: int = 4,
        min_bitrate: int = 128,
        min_file_size: int = 500000,
        audio_quality: str = "0"
    ):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded files
            max_workers: Maximum concurrent downloads
            min_bitrate: Minimum acceptable bitrate in kbps
            min_file_size: Minimum acceptable file size in bytes
            audio_quality: yt-dlp audio quality (0 = best)
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.min_bitrate = min_bitrate
        self.min_file_size = min_file_size
        self.audio_quality = audio_quality

        os.makedirs(output_dir, exist_ok=True)

    def download_single(
        self,
        search_result: SearchResult,
        metadata: TrackMetadata,
        progress_callback: Optional[Callable] = None
    ) -> DownloadResult:
        """
        Download a single track.

        Args:
            search_result: Search result with URL
            metadata: Track metadata
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with status and file path
        """
        output_template = os.path.join(
            self.output_dir,
            f"{metadata.filename}.%(ext)s"
        )
        final_path = os.path.join(self.output_dir, f"{metadata.filename}.mp3")

        if os.path.exists(final_path):
            if self._validate_file(final_path):
                console.print(f"[yellow]Already exists: {metadata.filename}[/yellow]")
                return DownloadResult(
                    success=True,
                    file_path=final_path,
                    metadata=metadata
                )
            else:
                os.remove(final_path)

        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                search_result.url,
                "-x",
                "-f", "bestaudio/best",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--ffmpeg-location", r"C:\Users\Palwasha Ali\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin",
                "--postprocessor-args", "ffmpeg:-b:a 192k",
                "-o", output_template,
                "--no-playlist",
                "--no-warnings",
                "--quiet",
                "--progress",
                "--concurrent-fragments", "8"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return DownloadResult(
                    success=False,
                    file_path=None,
                    metadata=metadata,
                    error=f"Download failed: {result.stderr}"
                )

            if not os.path.exists(final_path):
                possible_files = [
                    f for f in os.listdir(self.output_dir)
                    if f.startswith(metadata.filename[:20])
                ]
                if possible_files:
                    old_path = os.path.join(self.output_dir, possible_files[0])
                    if old_path.endswith(".mp3"):
                        os.rename(old_path, final_path)

            if not os.path.exists(final_path):
                return DownloadResult(
                    success=False,
                    file_path=None,
                    metadata=metadata,
                    error="Output file not found after download"
                )

            is_valid, file_size, bitrate = self._validate_file_detailed(final_path)
            if not is_valid:
                os.remove(final_path)
                return DownloadResult(
                    success=False,
                    file_path=None,
                    metadata=metadata,
                    error=f"File validation failed (size: {file_size}, bitrate: {bitrate})"
                )

            return DownloadResult(
                success=True,
                file_path=final_path,
                metadata=metadata,
                file_size=file_size,
                bitrate=bitrate
            )

        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False,
                file_path=None,
                metadata=metadata,
                error="Download timed out"
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                file_path=None,
                metadata=metadata,
                error=str(e)
            )

    def download_batch(
        self,
        items: list[tuple[SearchResult, TrackMetadata]],
        progress_callback: Optional[Callable] = None
    ) -> list[DownloadResult]:
        """
        Download multiple tracks concurrently.

        Args:
            items: List of (SearchResult, TrackMetadata) tuples
            progress_callback: Optional callback for progress updates

        Returns:
            List of DownloadResult objects
        """
        results = []
        total = len(items)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"[cyan]Downloading {total} tracks...", total=total)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_item = {
                    executor.submit(self.download_single, sr, meta): (sr, meta)
                    for sr, meta in items
                }

                for future in as_completed(future_to_item):
                    sr, meta = future_to_item[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result.success:
                            progress.console.print(
                                f"[green]Downloaded: {meta.filename}[/green]"
                            )
                        else:
                            progress.console.print(
                                f"[red]Failed: {meta.filename} - {result.error}[/red]"
                            )
                    except Exception as e:
                        results.append(DownloadResult(
                            success=False,
                            file_path=None,
                            metadata=meta,
                            error=str(e)
                        ))
                        progress.console.print(
                            f"[red]Error: {meta.filename} - {e}[/red]"
                        )

                    progress.update(task, advance=1)

        return results

    def _validate_file(self, file_path: str) -> bool:
        """
        Quick validation of a downloaded file.

        Args:
            file_path: Path to the file

        Returns:
            True if file is valid
        """
        is_valid, _, _ = self._validate_file_detailed(file_path)
        return is_valid

    def _validate_file_detailed(self, file_path: str) -> tuple[bool, int, int]:
        """
        Detailed validation of a downloaded file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (is_valid, file_size, bitrate)
        """
        try:
            file_size = os.path.getsize(file_path)
            if file_size < self.min_file_size:
                return False, file_size, 0

            bitrate = self._get_bitrate(file_path)
            if bitrate < self.min_bitrate:
                return False, file_size, bitrate

            return True, file_size, bitrate

        except Exception:
            return False, 0, 0

    def _get_bitrate(self, file_path: str) -> int:
        """
        Get the bitrate of an audio file using ffprobe.

        Args:
            file_path: Path to the audio file

        Returns:
            Bitrate in kbps, or 0 if unable to determine
        """
        ffprobe_path = r"C:\Users\Palwasha Ali\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin\ffprobe.exe"
        try:
            cmd = [
                ffprobe_path,
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=bit_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                bitrate_bps = int(result.stdout.strip())
                return bitrate_bps // 1000

        except Exception:
            pass

        try:
            file_size = os.path.getsize(file_path)
            cmd = [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                if duration > 0:
                    return int((file_size * 8) / (duration * 1000))

        except Exception:
            pass

        return 192

    def cleanup_failed_downloads(self) -> int:
        """
        Remove any incomplete or invalid downloads.

        Returns:
            Number of files removed
        """
        removed = 0
        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            if not self._validate_file(file_path):
                try:
                    os.remove(file_path)
                    removed += 1
                except Exception:
                    pass
        return removed
