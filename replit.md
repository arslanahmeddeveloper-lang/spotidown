# Spotify Downloader

## Overview

A CLI-based Spotify Downloader tool that fetches music metadata from Spotify and downloads matching audio files with embedded ID3 tags and album art.

## Project Architecture

### Core Modules

- **SpotifyClient** (`src/spotify_downloader/spotify_client.py`): Handles Spotify API authentication and metadata fetching with rate limiting
- **SearchEngine** (`src/spotify_downloader/search_engine.py`): Searches for audio matches using yt-dlp with retry logic
- **Downloader** (`src/spotify_downloader/downloader.py`): Multi-threaded download manager with file validation
- **MetadataManager** (`src/spotify_downloader/metadata_manager.py`): Embeds ID3 tags and album art using mutagen and ffmpeg

### Entry Points

- `main.py` - Main CLI entry point
- `src/spotify_downloader/cli.py` - Click-based CLI commands

## Technology Stack

- **Language**: Python 3.11
- **CLI Framework**: Click
- **Spotify API**: spotipy
- **Audio Download**: yt-dlp
- **Audio Processing**: ffmpeg
- **ID3 Tags**: mutagen
- **Console Output**: rich

## Authentication

The tool supports two authentication methods:

1. **Replit Spotify Integration** (recommended): Connect your Spotify account via Replit's integration. This handles OAuth automatically.

2. **Manual Credentials**: Set environment variables:
   - `SPOTIFY_CLIENT_ID` - Spotify API client ID  
   - `SPOTIFY_CLIENT_SECRET` - Spotify API client secret

## Commands

```bash
# Download a single track
python main.py track <spotify_url>

# Download a playlist
python main.py playlist <spotify_url> -w 4

# Download an album
python main.py album <spotify_url> -w 4

# Show downloaded files info
python main.py info

# Cleanup invalid downloads
python main.py cleanup
```

## Recent Changes

- Initial implementation with modular architecture
- Multi-threaded playlist/album downloads
- Retry logic for search failures
- File validation for quality assurance
