"""
SearchEngine - Handles searching for audio matches using yt-dlp.
"""

import subprocess
import json
import time
from typing import Optional
from dataclasses import dataclass

from rich.console import Console

from .spotify_client import TrackMetadata

console = Console()


@dataclass
class SearchResult:
    """Data class for search results."""
    url: str
    title: str
    duration: int
    view_count: int
    source: str
    quality_score: float


class SearchEngine:
    """
    Handles searching for audio matches using yt-dlp.
    
    Implements retry logic with different search queries for better matches.
    """

    def __init__(
        self,
        max_retries: int = 5,
        duration_tolerance: float = 0.30,
        min_quality_score: float = 0.3
    ):
        """
        Initialize the search engine.

        Args:
            max_retries: Maximum number of search attempts with different queries
            duration_tolerance: Allowed duration difference (percentage)
            min_quality_score: Minimum quality score to accept a result
        """
        self.max_retries = max_retries
        self.duration_tolerance = duration_tolerance
        self.min_quality_score = min_quality_score

    def search(self, metadata: TrackMetadata) -> Optional[SearchResult]:
        """
        Search for the best audio match for a track.

        Implements retry logic with different search queries.

        Args:
            metadata: Track metadata from Spotify

        Returns:
            Best matching SearchResult or None
        """
        search_queries = self._generate_search_queries(metadata)
        all_results = []

        for i, query in enumerate(search_queries[:self.max_retries]):
            console.print(f"[cyan]Searching ({i + 1}/{self.max_retries}): {query}[/cyan]")
            
            results = self._execute_search(query, max_results=10)
            if not results:
                time.sleep(0.3)
                continue

            best_match = self._find_best_match(results, metadata)
            if best_match:
                all_results.append(best_match)
                if best_match.quality_score >= self.min_quality_score:
                    console.print(
                        f"[green]Found match: {best_match.title} "
                        f"(score: {best_match.quality_score:.2f})[/green]"
                    )
                    return best_match

            time.sleep(0.3)

        if all_results:
            all_results.sort(key=lambda x: x.quality_score, reverse=True)
            best = all_results[0]
            console.print(
                f"[yellow]Using best available match: {best.title} "
                f"(score: {best.quality_score:.2f})[/yellow]"
            )
            return best

        console.print(f"[yellow]No match found for: {metadata.name}[/yellow]")
        return None

    def _generate_search_queries(self, metadata: TrackMetadata) -> list[str]:
        """
        Generate multiple search queries for retry logic.

        Args:
            metadata: Track metadata

        Returns:
            List of search queries in priority order
        """
        queries = []

        queries.append(f"{metadata.artist} {metadata.name}")

        queries.append(f"{metadata.artist} {metadata.name} official audio")

        queries.append(f"{metadata.name} {metadata.artist}")

        if metadata.isrc:
            queries.append(f"{metadata.isrc}")

        queries.append(f"{metadata.artist} {metadata.name} lyrics")

        queries.append(f"{metadata.name} audio")

        queries.append(f"{metadata.name} {metadata.album}")

        queries.append(f"{metadata.name} full song")

        artist_first = metadata.artist.split(",")[0].strip() if "," in metadata.artist else metadata.artist
        queries.append(f"{artist_first} {metadata.name}")

        return queries

    def _execute_search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Execute a search using yt-dlp.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of search result dictionaries
        """
        try:
            cmd = [
                "yt-dlp",
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--flat-playlist",
                "--no-warnings",
                "--quiet"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            results = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        results.append(data)
                    except json.JSONDecodeError:
                        continue

            return results

        except subprocess.TimeoutExpired:
            console.print("[yellow]Search timed out.[/yellow]")
            return []
        except Exception as e:
            console.print(f"[red]Search error: {e}[/red]")
            return []

    def _find_best_match(
        self,
        results: list[dict],
        metadata: TrackMetadata
    ) -> Optional[SearchResult]:
        """
        Find the best matching result based on quality scoring.

        Args:
            results: List of search results
            metadata: Original track metadata

        Returns:
            Best matching SearchResult or None
        """
        target_duration = metadata.duration_ms / 1000
        scored_results = []

        for result in results:
            try:
                duration = result.get("duration") or 0
                
                score = self._calculate_quality_score(result, metadata, target_duration)
                
                video_id = result.get("id") or result.get("url", "").split("watch?v=")[-1]
                url = result.get("url") or f"https://www.youtube.com/watch?v={video_id}"
                
                search_result = SearchResult(
                    url=url,
                    title=result.get("title", "Unknown"),
                    duration=duration if duration else int(target_duration),
                    view_count=result.get("view_count", 0) or 0,
                    source="youtube",
                    quality_score=score
                )
                scored_results.append(search_result)

            except Exception:
                continue

        if not scored_results:
            return None

        scored_results.sort(key=lambda x: x.quality_score, reverse=True)
        return scored_results[0]

    def _calculate_quality_score(
        self,
        result: dict,
        metadata: TrackMetadata,
        target_duration: float
    ) -> float:
        """
        Calculate a quality score for a search result.

        Scoring factors:
        - Title relevance (50%)
        - Duration match (25%)
        - View count popularity (15%)
        - Official/audio keywords (10%)

        Args:
            result: Search result dictionary
            metadata: Original track metadata
            target_duration: Target duration in seconds

        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        title = result.get("title", "").lower()

        artist_lower = metadata.artist.lower()
        track_lower = metadata.name.lower()
        
        title_score = 0.0
        artist_words = artist_lower.split()
        track_words = track_lower.split()
        
        for word in artist_words:
            if len(word) > 2 and word in title:
                title_score += 0.25
        for word in track_words:
            if len(word) > 2 and word in title:
                title_score += 0.25
        
        title_score = min(1.0, title_score)
        score += title_score * 0.5

        duration = result.get("duration") or 0
        if duration > 0 and target_duration > 0:
            duration_diff = abs(duration - target_duration) / max(target_duration, 1)
            if duration_diff <= self.duration_tolerance:
                duration_score = 1.0 - (duration_diff / self.duration_tolerance)
            else:
                duration_score = max(0, 0.5 - (duration_diff * 0.3))
            score += duration_score * 0.25
        else:
            score += 0.1

        view_count = result.get("view_count", 0) or 0
        if view_count > 0:
            import math
            popularity_score = min(1.0, math.log10(view_count + 1) / 8)
            score += popularity_score * 0.15
        else:
            score += 0.05

        official_keywords = ["official", "audio", "lyrics", "hd", "hq", "full"]
        bad_keywords = ["cover", "remix", "live", "karaoke", "instrumental", "acoustic", "slowed", "reverb"]
        
        keyword_score = 0.5
        for keyword in official_keywords:
            if keyword in title:
                keyword_score = min(1.0, keyword_score + 0.1)
        for keyword in bad_keywords:
            if keyword in title and keyword not in track_lower:
                keyword_score = max(0.0, keyword_score - 0.15)
        score += keyword_score * 0.1

        return min(1.0, max(0.1, score))

    def get_video_info(self, url: str) -> Optional[dict]:
        """
        Get detailed video information for a URL.

        Args:
            url: Video URL

        Returns:
            Video information dictionary or None
        """
        try:
            cmd = [
                "yt-dlp",
                url,
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--quiet"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)

        except Exception as e:
            console.print(f"[red]Failed to get video info: {e}[/red]")

        return None
