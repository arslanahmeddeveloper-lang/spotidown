"""
Spotify Downloader - A CLI tool to download music from Spotify.
"""

from .spotify_client import SpotifyClient
from .search_engine import SearchEngine
from .downloader import Downloader
from .metadata_manager import MetadataManager

__version__ = "1.0.0"
__all__ = ["SpotifyClient", "SearchEngine", "Downloader", "MetadataManager"]
