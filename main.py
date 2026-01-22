#!/usr/bin/env python3
"""
Spotify Downloader - Main entry point.

A CLI-based tool to download music from Spotify with high-quality audio
and embedded metadata.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from spotify_downloader.cli import main

if __name__ == "__main__":
    main()
