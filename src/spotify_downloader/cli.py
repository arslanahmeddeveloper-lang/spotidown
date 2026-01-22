"""
CLI - Command-line interface for Spotify Downloader.
"""

import os
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .spotify_client import SpotifyClient, TrackMetadata
from .search_engine import SearchEngine
from .downloader import Downloader, DownloadResult
from .metadata_manager import MetadataManager

console = Console()


def print_banner():
    """Print the application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                    Spotify Downloader v1.0                    ║
║          Download your favorite music from Spotify            ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner, style="cyan"))


def validate_credentials() -> bool:
    """Check if Spotify credentials are set."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        console.print(
            "[red]Error: Spotify credentials not found![/red]\n\n"
            "Please set the following environment variables:\n"
            "  - SPOTIFY_CLIENT_ID\n"
            "  - SPOTIFY_CLIENT_SECRET\n\n"
            "You can get these from: https://developer.spotify.com/dashboard"
        )
        return False
    return True


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Spotify Downloader - Download music from Spotify.

    A CLI tool to download tracks, playlists, and albums from Spotify
    with high-quality audio and embedded metadata.
    """
    pass


@cli.command()
@click.argument("url")
@click.option(
    "-o", "--output",
    default="downloads",
    help="Output directory for downloaded files"
)
@click.option(
    "-q", "--quality",
    default="0",
    help="Audio quality (0=best, 9=worst)"
)
@click.option(
    "--normalize/--no-normalize",
    default=False,
    help="Normalize audio levels"
)
def track(url: str, output: str, quality: str, normalize: bool):
    """
    Download a single track from Spotify.

    URL can be a Spotify track URL or URI.

    Example:
        spotify-dl track https://open.spotify.com/track/...
    """
    print_banner()
    
    if not validate_credentials():
        sys.exit(1)

    spotify = SpotifyClient()
    if not spotify.authenticate():
        sys.exit(1)

    console.print(f"\n[cyan]Fetching track metadata...[/cyan]")
    metadata = spotify.get_track(url)
    
    if not metadata:
        console.print("[red]Failed to fetch track metadata.[/red]")
        sys.exit(1)

    _print_track_info(metadata)

    result = _download_track(metadata, output, quality, normalize)
    
    if result and result.success:
        console.print(f"\n[green]Successfully downloaded: {result.file_path}[/green]")
    else:
        console.print("\n[red]Download failed.[/red]")
        sys.exit(1)


@cli.command()
@click.argument("url")
@click.option(
    "-o", "--output",
    default="downloads",
    help="Output directory for downloaded files"
)
@click.option(
    "-q", "--quality",
    default="0",
    help="Audio quality (0=best, 9=worst)"
)
@click.option(
    "-w", "--workers",
    default=4,
    help="Number of concurrent downloads"
)
@click.option(
    "--normalize/--no-normalize",
    default=False,
    help="Normalize audio levels"
)
def playlist(url: str, output: str, quality: str, workers: int, normalize: bool):
    """
    Download all tracks from a Spotify playlist.

    URL can be a Spotify playlist URL or URI.

    Example:
        spotify-dl playlist https://open.spotify.com/playlist/...
    """
    print_banner()
    
    if not validate_credentials():
        sys.exit(1)

    spotify = SpotifyClient()
    if not spotify.authenticate():
        sys.exit(1)

    console.print(f"\n[cyan]Fetching playlist tracks...[/cyan]")
    tracks = spotify.get_playlist_tracks(url)
    
    if not tracks:
        console.print("[red]No tracks found in playlist.[/red]")
        sys.exit(1)

    console.print(f"\n[green]Found {len(tracks)} tracks to download.[/green]\n")

    results = _download_batch(tracks, output, quality, workers, normalize)
    _print_summary(results)


@cli.command()
@click.argument("url")
@click.option(
    "-o", "--output",
    default="downloads",
    help="Output directory for downloaded files"
)
@click.option(
    "-q", "--quality",
    default="0",
    help="Audio quality (0=best, 9=worst)"
)
@click.option(
    "-w", "--workers",
    default=4,
    help="Number of concurrent downloads"
)
@click.option(
    "--normalize/--no-normalize",
    default=False,
    help="Normalize audio levels"
)
def album(url: str, output: str, quality: str, workers: int, normalize: bool):
    """
    Download all tracks from a Spotify album.

    URL can be a Spotify album URL or URI.

    Example:
        spotify-dl album https://open.spotify.com/album/...
    """
    print_banner()
    
    if not validate_credentials():
        sys.exit(1)

    spotify = SpotifyClient()
    if not spotify.authenticate():
        sys.exit(1)

    console.print(f"\n[cyan]Fetching album tracks...[/cyan]")
    tracks = spotify.get_album_tracks(url)
    
    if not tracks:
        console.print("[red]No tracks found in album.[/red]")
        sys.exit(1)

    console.print(f"\n[green]Found {len(tracks)} tracks to download.[/green]\n")

    results = _download_batch(tracks, output, quality, workers, normalize)
    _print_summary(results)


@cli.command()
@click.option(
    "-d", "--directory",
    default="downloads",
    help="Directory to scan"
)
def info(directory: str):
    """
    Show information about downloaded files.

    Displays metadata and quality information for all MP3 files
    in the specified directory.
    """
    print_banner()
    
    if not os.path.exists(directory):
        console.print(f"[red]Directory not found: {directory}[/red]")
        sys.exit(1)

    manager = MetadataManager()
    files = [f for f in os.listdir(directory) if f.endswith(".mp3")]
    
    if not files:
        console.print(f"[yellow]No MP3 files found in {directory}[/yellow]")
        return

    table = Table(title="Downloaded Tracks")
    table.add_column("File", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Artist", style="yellow")
    table.add_column("Duration", style="magenta")
    table.add_column("Bitrate", style="blue")
    table.add_column("Size", style="white")

    for filename in sorted(files):
        file_path = os.path.join(directory, filename)
        file_info = manager.get_file_info(file_path)
        
        if file_info:
            duration = f"{int(file_info['duration'] // 60)}:{int(file_info['duration'] % 60):02d}"
            size = f"{file_info['file_size'] / (1024 * 1024):.1f} MB"
            
            table.add_row(
                filename[:30] + "..." if len(filename) > 30 else filename,
                file_info.get("title", "Unknown")[:20],
                file_info.get("artist", "Unknown")[:20],
                duration,
                f"{file_info['bitrate']} kbps",
                size
            )

    console.print(table)


@cli.command()
@click.option(
    "-d", "--directory",
    default="downloads",
    help="Directory to clean"
)
def cleanup(directory: str):
    """
    Remove invalid or incomplete downloads.

    Scans the download directory and removes files that don't meet
    quality thresholds.
    """
    print_banner()
    
    if not os.path.exists(directory):
        console.print(f"[red]Directory not found: {directory}[/red]")
        sys.exit(1)

    downloader = Downloader(output_dir=directory)
    removed = downloader.cleanup_failed_downloads()
    
    console.print(f"[green]Removed {removed} invalid file(s).[/green]")


def _print_track_info(metadata: TrackMetadata):
    """Print track information in a formatted table."""
    table = Table(title="Track Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Title", metadata.name)
    table.add_row("Artist", metadata.artist)
    table.add_row("Album", metadata.album)
    table.add_row("Duration", f"{metadata.duration_ms // 60000}:{(metadata.duration_ms // 1000) % 60:02d}")
    if metadata.isrc:
        table.add_row("ISRC", metadata.isrc)
    if metadata.release_date:
        table.add_row("Release Date", metadata.release_date)
    
    console.print(table)


def _download_track(
    metadata: TrackMetadata,
    output: str,
    quality: str,
    normalize: bool
) -> Optional[DownloadResult]:
    """Download a single track with metadata embedding."""
    search_engine = SearchEngine()
    downloader = Downloader(output_dir=output, audio_quality=quality)
    metadata_manager = MetadataManager()

    console.print(f"\n[cyan]Searching for audio match...[/cyan]")
    search_result = search_engine.search(metadata)
    
    if not search_result:
        console.print("[red]Could not find a suitable audio match.[/red]")
        return None

    console.print(f"\n[cyan]Downloading...[/cyan]")
    result = downloader.download_single(search_result, metadata)
    
    if result.success and result.file_path:
        console.print(f"\n[cyan]Embedding metadata...[/cyan]")
        metadata_manager.embed_metadata(result.file_path, metadata)
        
        if normalize:
            console.print(f"[cyan]Normalizing audio...[/cyan]")
            metadata_manager.normalize_audio(result.file_path)

    return result


def _download_batch(
    tracks: list[TrackMetadata],
    output: str,
    quality: str,
    workers: int,
    normalize: bool
) -> list[DownloadResult]:
    """Download multiple tracks with multi-threading."""
    search_engine = SearchEngine()
    downloader = Downloader(output_dir=output, audio_quality=quality, max_workers=workers)
    metadata_manager = MetadataManager()

    console.print("[cyan]Searching for audio matches...[/cyan]\n")
    
    items = []
    for metadata in tracks:
        search_result = search_engine.search(metadata)
        if search_result:
            items.append((search_result, metadata))
        else:
            console.print(f"[yellow]Skipping: {metadata.name} (no match found)[/yellow]")

    if not items:
        console.print("[red]No tracks could be matched.[/red]")
        return []

    console.print(f"\n[cyan]Downloading {len(items)} tracks...[/cyan]\n")
    results = downloader.download_batch(items)

    console.print(f"\n[cyan]Embedding metadata...[/cyan]")
    for result in results:
        if result.success and result.file_path:
            metadata_manager.embed_metadata(result.file_path, result.metadata)
            if normalize:
                metadata_manager.normalize_audio(result.file_path)

    return results


def _print_summary(results: list[DownloadResult]):
    """Print a summary of download results."""
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    console.print("\n")
    table = Table(title="Download Summary")
    table.add_column("Status", style="bold")
    table.add_column("Count", style="bold")
    
    table.add_row("[green]Successful[/green]", str(successful))
    table.add_row("[red]Failed[/red]", str(failed))
    table.add_row("Total", str(len(results)))
    
    console.print(table)

    if failed > 0:
        console.print("\n[yellow]Failed tracks:[/yellow]")
        for result in results:
            if not result.success:
                console.print(f"  - {result.metadata.name}: {result.error}")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
