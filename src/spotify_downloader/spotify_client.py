"""
SpotifyClient - Handles Spotify API authentication and metadata fetching.
"""

import os
import time
from typing import Optional
from dataclasses import dataclass

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from rich.console import Console

console = Console()


@dataclass
class TrackMetadata:
    """Data class for storing track metadata."""
    track_id: str
    name: str
    artist: str
    album: str
    album_art_url: Optional[str]
    isrc: Optional[str]
    duration_ms: int
    release_date: Optional[str]

    @property
    def search_query(self) -> str:
        """Generate a search query for the track."""
        return f"{self.artist} - {self.name}"

    @property
    def filename(self) -> str:
        """Generate a safe filename for the track."""
        safe_name = "".join(c for c in self.name if c.isalnum() or c in " -_").strip()
        safe_artist = "".join(c for c in self.artist if c.isalnum() or c in " -_").strip()
        return f"{safe_artist} - {safe_name}"


class SpotifyClient:
    """
    Handles Spotify API authentication and metadata fetching.
    
    Implements rate limiting and retry logic for API calls.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the Spotify client.

        Args:
            client_id: Spotify API client ID (defaults to env var SPOTIFY_CLIENT_ID)
            client_secret: Spotify API client secret (defaults to env var SPOTIFY_CLIENT_SECRET)
            max_retries: Maximum number of retries for API calls
            retry_delay: Base delay between retries in seconds
        """
        self.client_id = client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._spotify: Optional[spotipy.Spotify] = None

    def authenticate(self) -> bool:
        """
        Authenticate with Spotify API.

        Returns:
            True if authentication was successful, False otherwise.
        """
        if not self.client_id or not self.client_secret:
            console.print(
                "[red]Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET "
                "environment variables must be set.[/red]"
            )
            return False

        try:
            auth_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self._spotify = spotipy.Spotify(auth_manager=auth_manager)
            self._spotify.search(q="test", limit=1)
            console.print("[green]Successfully authenticated with Spotify API.[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Authentication failed: {e}[/red]")
            return False

    def _make_api_call(self, func, *args, **kwargs):
        """
        Make an API call with retry logic for rate limits.

        Args:
            func: The API function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the API call

        Raises:
            Exception: If all retries are exhausted
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:
                    retry_after = int(e.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                    console.print(f"[yellow]Rate limited. Waiting {retry_after}s...[/yellow]")
                    time.sleep(retry_after)
                elif e.http_status >= 500:
                    delay = self.retry_delay * (2 ** attempt)
                    console.print(f"[yellow]Server error. Retrying in {delay}s...[/yellow]")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    console.print(f"[yellow]Error: {e}. Retrying in {delay}s...[/yellow]")
                    time.sleep(delay)
                else:
                    raise
        raise Exception(f"Failed after {self.max_retries} attempts")

    def get_track(self, track_url: str) -> Optional[TrackMetadata]:
        """
        Fetch metadata for a single track.

        Args:
            track_url: Spotify track URL or URI

        Returns:
            TrackMetadata object or None if failed
        """
        if not self._spotify:
            console.print("[red]Not authenticated. Call authenticate() first.[/red]")
            return None

        try:
            track_id = self._extract_id(track_url, "track")
            track = self._make_api_call(self._spotify.track, track_id)
            return self._parse_track(track)
        except Exception as e:
            console.print(f"[red]Failed to fetch track: {e}[/red]")
            return None

    def get_playlist_tracks(self, playlist_url: str) -> list[TrackMetadata]:
        """
        Fetch all tracks from a playlist.

        Args:
            playlist_url: Spotify playlist URL or URI

        Returns:
            List of TrackMetadata objects
        """
        if not self._spotify:
            console.print("[red]Not authenticated. Call authenticate() first.[/red]")
            return []

        tracks = []
        try:
            playlist_id = self._extract_id(playlist_url, "playlist")
            offset = 0
            limit = 100

            while True:
                results = self._make_api_call(
                    self._spotify.playlist_tracks,
                    playlist_id,
                    offset=offset,
                    limit=limit
                )

                for item in results["items"]:
                    if item["track"] and item["track"]["id"]:
                        metadata = self._parse_track(item["track"])
                        if metadata:
                            tracks.append(metadata)

                if results["next"] is None:
                    break
                offset += limit

            console.print(f"[green]Found {len(tracks)} tracks in playlist.[/green]")
            return tracks

        except Exception as e:
            console.print(f"[red]Failed to fetch playlist: {e}[/red]")
            return tracks

    def get_album_tracks(self, album_url: str) -> list[TrackMetadata]:
        """
        Fetch all tracks from an album.

        Args:
            album_url: Spotify album URL or URI

        Returns:
            List of TrackMetadata objects
        """
        if not self._spotify:
            console.print("[red]Not authenticated. Call authenticate() first.[/red]")
            return []

        tracks = []
        try:
            album_id = self._extract_id(album_url, "album")
            album = self._make_api_call(self._spotify.album, album_id)
            album_name = album["name"]
            album_art_url = album["images"][0]["url"] if album["images"] else None
            release_date = album.get("release_date")

            for item in album["tracks"]["items"]:
                artist = ", ".join(a["name"] for a in item["artists"])
                metadata = TrackMetadata(
                    track_id=item["id"],
                    name=item["name"],
                    artist=artist,
                    album=album_name,
                    album_art_url=album_art_url,
                    isrc=None,
                    duration_ms=item["duration_ms"],
                    release_date=release_date
                )
                tracks.append(metadata)

            console.print(f"[green]Found {len(tracks)} tracks in album.[/green]")
            return tracks

        except Exception as e:
            console.print(f"[red]Failed to fetch album: {e}[/red]")
            return tracks

    def _extract_id(self, url: str, content_type: str) -> str:
        """
        Extract the Spotify ID from a URL or URI.

        Args:
            url: Spotify URL or URI
            content_type: Type of content (track, playlist, album)

        Returns:
            The extracted ID
        """
        if url.startswith("spotify:"):
            parts = url.split(":")
            return parts[-1]

        if "open.spotify.com" in url:
            parts = url.split("/")
            for i, part in enumerate(parts):
                if part == content_type and i + 1 < len(parts):
                    id_part = parts[i + 1].split("?")[0]
                    return id_part

        return url

    def _parse_track(self, track: dict) -> Optional[TrackMetadata]:
        """
        Parse a track dict into TrackMetadata.

        Args:
            track: Raw track data from Spotify API

        Returns:
            TrackMetadata object or None
        """
        try:
            artist = ", ".join(a["name"] for a in track["artists"])
            album = track["album"]["name"]
            album_art_url = None
            if track["album"]["images"]:
                album_art_url = track["album"]["images"][0]["url"]

            isrc = None
            if "external_ids" in track and "isrc" in track["external_ids"]:
                isrc = track["external_ids"]["isrc"]

            return TrackMetadata(
                track_id=track["id"],
                name=track["name"],
                artist=artist,
                album=album,
                album_art_url=album_art_url,
                isrc=isrc,
                duration_ms=track["duration_ms"],
                release_date=track["album"].get("release_date")
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to parse track: {e}[/yellow]")
            return None
