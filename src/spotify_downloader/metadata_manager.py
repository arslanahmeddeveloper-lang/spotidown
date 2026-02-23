"""
MetadataManager - Handles ID3 tags and ffmpeg post-processing.
"""

import os
import subprocess
import tempfile
from typing import Optional

import requests
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3,
    TIT2,
    TPE1,
    TALB,
    TDRC,
    APIC,
    ID3NoHeaderError
)
from rich.console import Console

from .spotify_client import TrackMetadata

console = Console()


class MetadataManager:
    """
    Handles embedding ID3 tags and album art into MP3 files.
    
    Uses mutagen for ID3 tag manipulation and ffmpeg for audio processing.
    """

    def __init__(self, target_bitrate: int = 320):
        """
        Initialize the metadata manager.

        Args:
            target_bitrate: Target bitrate for audio conversion in kbps
        """
        self.target_bitrate = target_bitrate
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; SpotifyDownloader/1.0)"
        })

    def embed_metadata(
        self,
        file_path: str,
        metadata: TrackMetadata,
        convert_bitrate: bool = False
    ) -> bool:
        """
        Embed metadata and album art into an MP3 file.

        Args:
            file_path: Path to the MP3 file
            metadata: Track metadata to embed
            convert_bitrate: Whether to convert to target bitrate first

        Returns:
            True if successful
        """
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            return False

        try:
            if convert_bitrate:
                converted_path = self._convert_bitrate(file_path)
                if converted_path:
                    os.replace(converted_path, file_path)

            self._embed_id3_tags(file_path, metadata)

            if metadata.album_art_url:
                self._embed_album_art(file_path, metadata.album_art_url)

            console.print(f"[green]Embedded metadata: {metadata.filename}[/green]")
            return True

        except Exception as e:
            console.print(f"[red]Failed to embed metadata: {e}[/red]")
            return False

    def _embed_id3_tags(self, file_path: str, metadata: TrackMetadata) -> None:
        """
        Embed ID3 tags into an MP3 file.

        Args:
            file_path: Path to the MP3 file
            metadata: Track metadata
        """
        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        audio.tags.add(TIT2(encoding=3, text=metadata.name))

        audio.tags.add(TPE1(encoding=3, text=metadata.artist))

        audio.tags.add(TALB(encoding=3, text=metadata.album))

        if metadata.release_date:
            year = metadata.release_date.split("-")[0]
            audio.tags.add(TDRC(encoding=3, text=year))

        audio.save()

    def _embed_album_art(self, file_path: str, art_url: str) -> None:
        """
        Download and embed album art into an MP3 file.

        Args:
            file_path: Path to the MP3 file
            art_url: URL of the album art
        """
        try:
            response = self._session.get(art_url, timeout=10)
            response.raise_for_status()
            image_data = response.content

            mime_type = response.headers.get("Content-Type", "image/jpeg")

            audio = MP3(file_path, ID3=ID3)
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc="Cover",
                    data=image_data
                )
            )
            audio.save()

        except Exception as e:
            console.print(f"[yellow]Failed to embed album art: {e}[/yellow]")

    def _convert_bitrate(self, file_path: str) -> Optional[str]:
        """
        Convert an audio file to the target bitrate using ffmpeg.

        Args:
            file_path: Path to the input file

        Returns:
            Path to the converted file, or None if failed
        """
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            ffmpeg_path = r"C:\Users\Palwasha Ali\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
            cmd = [
                ffmpeg_path,
                "-i", file_path,
                "-b:a", f"{self.target_bitrate}k",
                "-y",
                "-loglevel", "error",
                temp_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and os.path.exists(temp_path):
                return temp_path
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return None

        except Exception as e:
            console.print(f"[yellow]Bitrate conversion failed: {e}[/yellow]")
            return None

    def normalize_audio(self, file_path: str) -> bool:
        """
        Normalize audio levels using ffmpeg.

        Args:
            file_path: Path to the audio file

        Returns:
            True if successful
        """
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            ffmpeg_path = r"C:\Users\Palwasha Ali\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
            cmd = [
                ffmpeg_path,
                "-i", file_path,
                "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-b:a", f"{self.target_bitrate}k",
                "-y",
                "-loglevel", "error",
                temp_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0 and os.path.exists(temp_path):
                os.replace(temp_path, file_path)
                return True
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

        except Exception as e:
            console.print(f"[yellow]Audio normalization failed: {e}[/yellow]")
            return False

    def batch_embed_metadata(
        self,
        items: list[tuple[str, TrackMetadata]]
    ) -> tuple[int, int]:
        """
        Embed metadata into multiple files.

        Args:
            items: List of (file_path, metadata) tuples

        Returns:
            Tuple of (successful_count, failed_count)
        """
        success = 0
        failed = 0

        for file_path, metadata in items:
            if self.embed_metadata(file_path, metadata):
                success += 1
            else:
                failed += 1

        return success, failed

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get information about an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            Dictionary with file information
        """
        try:
            audio = MP3(file_path)
            
            info = {
                "duration": audio.info.length,
                "bitrate": audio.info.bitrate // 1000,
                "sample_rate": audio.info.sample_rate,
                "channels": audio.info.channels,
                "file_size": os.path.getsize(file_path)
            }

            if audio.tags:
                info["title"] = str(audio.tags.get("TIT2", "Unknown"))
                info["artist"] = str(audio.tags.get("TPE1", "Unknown"))
                info["album"] = str(audio.tags.get("TALB", "Unknown"))

            return info

        except Exception as e:
            console.print(f"[red]Failed to get file info: {e}[/red]")
            return None
