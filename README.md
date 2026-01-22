# Spotify Downloader

A CLI-based tool to download music from Spotify with high-quality audio and embedded metadata.

## Features

- **Track Downloads**: Download individual tracks with full metadata
- **Playlist Support**: Download entire playlists with multi-threaded downloading
- **Album Support**: Download complete albums
- **High-Quality Audio**: Configurable audio quality settings
- **Metadata Embedding**: Automatic ID3 tags (Title, Artist, Album, Year) and album art
- **Smart Search**: Retry logic with multiple search queries for best matches
- **Validation**: File size and bitrate validation to ensure quality
- **Audio Normalization**: Optional audio level normalization

## Requirements

### System Dependencies

- Python 3.9 or higher
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Audio search and download
- [FFmpeg](https://ffmpeg.org/) - Audio conversion and processing

### Python Dependencies

```bash
pip install -r requirements.txt
```

## Setup

### 1. Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details (name, description)
5. Copy your **Client ID** and **Client Secret**

### 2. Set Environment Variables

```bash
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
```

Or create a `.env` file in the project root:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

## Usage

### Download a Single Track

```bash
python main.py track "https://open.spotify.com/track/..."
```

### Download a Playlist

```bash
python main.py playlist "https://open.spotify.com/playlist/..." -w 4
```

Options:
- `-w, --workers`: Number of concurrent downloads (default: 4)

### Download an Album

```bash
python main.py album "https://open.spotify.com/album/..." -w 4
```

### Common Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output directory (default: `downloads`) |
| `-q, --quality` | Audio quality (0=best, 9=worst) |
| `--normalize` | Normalize audio levels |

### View Downloaded Files Info

```bash
python main.py info -d downloads
```

### Cleanup Invalid Downloads

```bash
python main.py cleanup -d downloads
```

## Project Structure

```
spotify-downloader/
├── src/
│   └── spotify_downloader/
│       ├── __init__.py          # Package initialization
│       ├── cli.py               # CLI commands and entry point
│       ├── spotify_client.py    # Spotify API client
│       ├── search_engine.py     # Audio search with yt-dlp
│       ├── downloader.py        # Multi-threaded downloader
│       └── metadata_manager.py  # ID3 tags and ffmpeg processing
├── downloads/                   # Default output directory
├── main.py                      # Main entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Architecture

### SpotifyClient

Handles Spotify API authentication and metadata fetching:
- OAuth2 authentication with client credentials
- Track, playlist, and album metadata retrieval
- Rate limiting with exponential backoff
- ISRC code extraction for accurate matching

### SearchEngine

Implements intelligent audio search:
- Multiple search query generation for retry logic
- Quality scoring based on duration, title, popularity
- Filters out covers, remixes, and karaoke versions
- ISRC-based search for accurate matches

### Downloader

Multi-threaded download manager:
- Concurrent downloads with configurable workers
- File validation (size and bitrate thresholds)
- Progress tracking with rich console output
- Automatic retry on failure

### MetadataManager

Handles post-processing:
- ID3 tag embedding (Title, Artist, Album, Year)
- Album art download and embedding
- Bitrate conversion with FFmpeg
- Audio normalization

## Quality Validation

Downloaded files are validated against:
- **Minimum file size**: 500KB
- **Minimum bitrate**: 128kbps

Files that don't meet these thresholds are automatically rejected.

## Error Handling

- **API Rate Limits**: Automatic retry with exponential backoff
- **Network Timeouts**: Configurable timeout with retry logic
- **Search Failures**: Multiple search queries attempted
- **Download Failures**: Files validated and redownloaded if needed

## Legal Notice

This tool is intended for personal use only. Ensure you have the right to download any content you request. The developers are not responsible for any misuse of this tool.

## License

MIT License
