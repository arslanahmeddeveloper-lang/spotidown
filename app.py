"""
Spotify Downloader Web Application (FastAPI Version)

A beautiful web interface for downloading music from Spotify.
"""

import os
import sys
import uuid
import threading
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from spotify_downloader.spotify_client import SpotifyClient
from spotify_downloader.search_engine import SearchEngine
from spotify_downloader.downloader import Downloader
from spotify_downloader.metadata_manager import MetadataManager

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

download_status = {}

class TrackRequest(BaseModel):
    url: str

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/fetch")
async def fetch_track(data: TrackRequest):
    """Fetch track metadata from Spotify."""
    url = data.url.strip()
    
    if not url:
        return JSONResponse(status_code=400, content={"error": "Please provide a Spotify URL"})
    
    if "open.spotify.com/track" not in url and "spotify:track:" not in url:
        return JSONResponse(status_code=400, content={"error": "Please provide a valid Spotify track URL"})
    
    try:
        spotify = SpotifyClient()
        if not spotify.authenticate():
            return JSONResponse(status_code=500, content={"error": "Failed to authenticate with Spotify"})
        
        metadata = spotify.get_track(url)
        if not metadata:
            return JSONResponse(status_code=404, content={"error": "Could not fetch track information"})
        
        return {
            "success": True,
            "track": {
                "id": metadata.track_id,
                "name": metadata.name,
                "artist": metadata.artist,
                "album": metadata.album,
                "album_art": metadata.album_art_url,
                "duration_ms": metadata.duration_ms,
                "duration": f"{metadata.duration_ms // 60000}:{(metadata.duration_ms // 1000) % 60:02d}",
                "isrc": metadata.isrc,
                "release_date": metadata.release_date,
                "filename": metadata.filename
            }
        }
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/download")
async def download_track(data: TrackRequest):
    """Start downloading a track."""
    url = data.url.strip()
    
    if not url:
        return JSONResponse(status_code=400, content={"error": "Please provide a Spotify URL"})
    
    download_id = str(uuid.uuid4())
    download_status[download_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing...",
        "file_path": None,
        "error": None
    }
    
    thread = threading.Thread(
        target=process_download,
        args=(download_id, url)
    )
    thread.start()
    
    return {
        "success": True,
        "download_id": download_id
    }

def process_download(download_id: str, url: str):
    """Process the download in a background thread."""
    try:
        download_status[download_id]["status"] = "authenticating"
        download_status[download_id]["message"] = "Connecting to Spotify..."
        download_status[download_id]["progress"] = 10
        
        spotify = SpotifyClient()
        if not spotify.authenticate():
            download_status[download_id]["status"] = "error"
            download_status[download_id]["error"] = "Failed to authenticate with Spotify"
            return
        
        download_status[download_id]["status"] = "fetching"
        download_status[download_id]["message"] = "Fetching track metadata..."
        download_status[download_id]["progress"] = 20
        
        metadata = spotify.get_track(url)
        if not metadata:
            download_status[download_id]["status"] = "error"
            download_status[download_id]["error"] = "Could not fetch track information"
            return
        
        download_status[download_id]["status"] = "searching"
        download_status[download_id]["message"] = "Searching for audio source..."
        download_status[download_id]["progress"] = 40
        
        search_engine = SearchEngine()
        search_result = search_engine.search(metadata)
        
        if not search_result:
            download_status[download_id]["status"] = "error"
            download_status[download_id]["error"] = "Could not find a matching audio source"
            return
        
        download_status[download_id]["status"] = "downloading"
        download_status[download_id]["message"] = "Downloading audio..."
        download_status[download_id]["progress"] = 60
        
        downloader = Downloader(output_dir=DOWNLOAD_DIR)
        result = downloader.download_single(search_result, metadata)
        
        if not result.success or not result.file_path:
            download_status[download_id]["status"] = "error"
            download_status[download_id]["error"] = result.error or "Download failed"
            return
        
        download_status[download_id]["status"] = "processing"
        download_status[download_id]["message"] = "Adding metadata and album art..."
        download_status[download_id]["progress"] = 85
        
        metadata_manager = MetadataManager()
        metadata_manager.embed_metadata(result.file_path, metadata)
        
        download_status[download_id]["status"] = "complete"
        download_status[download_id]["message"] = "Download complete!"
        download_status[download_id]["progress"] = 100
        download_status[download_id]["file_path"] = result.file_path
        download_status[download_id]["filename"] = f"{metadata.filename}.mp3"
        
    except Exception as e:
        import traceback
        download_status[download_id]["status"] = "error"
        download_status[download_id]["error"] = f"{str(e)} | {traceback.format_exc()}"


@app.get("/api/status/{download_id}")
async def get_status(download_id: str):
    """Get the status of a download."""
    if download_id not in download_status:
        return JSONResponse(status_code=404, content={"error": "Download not found"})
    
    return download_status[download_id]


@app.get("/api/file/{download_id}")
async def get_file(download_id: str):
    """Download the completed file."""
    if download_id not in download_status:
        return JSONResponse(status_code=404, content={"error": "Download not found"})
    
    status = download_status[download_id]
    if status["status"] != "complete" or not status.get("file_path"):
        return JSONResponse(status_code=400, content={"error": "File not ready"})
    
    file_path = status["file_path"]
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    
    return FileResponse(
        path=file_path,
        filename=status.get("filename", "download.mp3"),
        media_type="audio/mpeg"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
