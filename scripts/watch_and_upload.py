#!/usr/bin/env python3
"""
Ridgemont Catalog Manager - Watch & Upload Script
==================================================
Monitors a folder for new audio files, extracts metadata,
uploads to Cloudflare R2, and updates the catalog.

Usage:
    python watch_and_upload.py

Requirements:
    pip install watchdog mutagen boto3 python-dotenv

Environment Variables (in .env file):
    CLOUDFLARE_ACCOUNT_ID=your_account_id
    CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
    CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
    R2_BUCKET_NAME=ridgemont-studio
"""

import os
import sys
import json
import re
import shutil
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Third-party imports
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3
    from mutagen.wave import WAVE
    import boto3
    from botocore.config import Config
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("\nInstall required packages:")
    print("  pip install watchdog mutagen boto3 python-dotenv")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
WATCH_FOLDER = Path.home() / "Music" / "Ridgemont-Upload"
COMPLETED_FOLDER = WATCH_FOLDER / "Completed"
CATALOG_MANAGER_ROOT = Path(__file__).parent.parent
CATALOG_JSON_PATH = CATALOG_MANAGER_ROOT / "data" / "catalog.json"

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.mp3', '.wav'}

# Artist name to act_id mapping
# Add new artists here as needed
ARTIST_TO_ACT_ID = {
    # Primary artist names
    "frozen cloud": "FROZEN_CLOUD",
    "bajan sun": "BAJAN_SUN",
    "park bellevue": "PARK_BELLEVUE",
    # Pseudonyms / Aliases
    "honest mile": "FROZEN_CLOUD",
    "echoes of jahara": "FROZEN_CLOUD",
    # Add more mappings as you add acts
}


# =============================================================================
# R2 CLIENT
# =============================================================================

class R2Client:
    """Cloudflare R2 storage client using S3-compatible API."""

    def __init__(self):
        load_dotenv(CATALOG_MANAGER_ROOT / ".env")

        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "ridgemont-studio")

        if not all([self.account_id, self.access_key, self.secret_key]):
            raise ValueError(
                "Missing R2 credentials. Please set these in .env:\n"
                "  CLOUDFLARE_ACCOUNT_ID\n"
                "  CLOUDFLARE_R2_ACCESS_KEY_ID\n"
                "  CLOUDFLARE_R2_SECRET_ACCESS_KEY"
            )

        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in R2."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except:
            return False

    def upload_file(self, local_path: Path, r2_key: str, content_type: str = None) -> bool:
        """Upload a file to R2."""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.client.upload_file(
                str(local_path),
                self.bucket_name,
                r2_key,
                ExtraArgs=extra_args
            )
            print(f"  [R2] Uploaded: {r2_key}")
            return True
        except Exception as e:
            print(f"  [R2] Upload failed: {e}")
            return False

    def upload_json(self, data: dict, r2_key: str) -> bool:
        """Upload JSON data to R2."""
        try:
            json_bytes = json.dumps(data, indent=2).encode('utf-8')
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=r2_key,
                Body=json_bytes,
                ContentType='application/json'
            )
            print(f"  [R2] Updated: {r2_key}")
            return True
        except Exception as e:
            print(f"  [R2] JSON upload failed: {e}")
            return False

    def get_json(self, r2_key: str) -> Optional[dict]:
        """Download and parse JSON from R2."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=r2_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except:
            return None


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from audio file using ID3 tags."""

    metadata = {
        "title": file_path.stem,  # Default to filename
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "year": None,
        "genre": None,
        "duration_seconds": None,
        "bpm": None,
    }

    try:
        if file_path.suffix.lower() == '.mp3':
            audio = MP3(file_path)
            metadata["duration_seconds"] = int(audio.info.length) if audio.info.length else None

            if audio.tags:
                # Title
                if 'TIT2' in audio.tags:
                    metadata["title"] = str(audio.tags['TIT2'])

                # Artist
                if 'TPE1' in audio.tags:
                    metadata["artist"] = str(audio.tags['TPE1'])
                elif 'TPE2' in audio.tags:
                    metadata["artist"] = str(audio.tags['TPE2'])

                # Album
                if 'TALB' in audio.tags:
                    metadata["album"] = str(audio.tags['TALB'])

                # Year
                if 'TDRC' in audio.tags:
                    year_str = str(audio.tags['TDRC'])
                    if year_str and len(year_str) >= 4:
                        metadata["year"] = int(year_str[:4])
                elif 'TYER' in audio.tags:
                    metadata["year"] = int(str(audio.tags['TYER']))

                # Genre
                if 'TCON' in audio.tags:
                    metadata["genre"] = str(audio.tags['TCON'])

                # BPM
                if 'TBPM' in audio.tags:
                    try:
                        metadata["bpm"] = int(float(str(audio.tags['TBPM'])))
                    except:
                        pass

        elif file_path.suffix.lower() == '.wav':
            audio = WAVE(file_path)
            metadata["duration_seconds"] = int(audio.info.length) if audio.info.length else None
            # WAV files typically don't have rich metadata

    except Exception as e:
        print(f"  [WARNING] Could not extract metadata: {e}")

    return metadata


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in file paths."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = sanitized.strip('. ')
    return sanitized or "Unknown"


def get_act_id(artist_name: str) -> str:
    """Convert artist name to act_id."""
    normalized = artist_name.lower().strip()

    if normalized in ARTIST_TO_ACT_ID:
        return ARTIST_TO_ACT_ID[normalized]

    # Generate act_id from artist name (UPPER_SNAKE_CASE)
    act_id = re.sub(r'[^a-z0-9]+', '_', normalized).upper().strip('_')
    return act_id or "UNKNOWN"


def generate_song_id() -> str:
    """Generate a unique song ID in format RS-YYYY-NNNN."""
    year = datetime.now().year
    # Use timestamp-based number for uniqueness
    num = int(datetime.now().strftime("%m%d%H%M"))
    return f"RS-{year}-{num:04d}"


# =============================================================================
# CATALOG MANAGEMENT
# =============================================================================

def load_catalog() -> Dict[str, Any]:
    """Load the catalog.json file."""
    if CATALOG_JSON_PATH.exists():
        with open(CATALOG_JSON_PATH, 'r') as f:
            return json.load(f)
    return {"songs": [], "writers": [], "contacts": [], "opportunities": []}


def save_catalog(catalog: Dict[str, Any]) -> None:
    """Save the catalog.json file."""
    # Create backup first
    if CATALOG_JSON_PATH.exists():
        backup_dir = CATALOG_MANAGER_ROOT / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"catalog_backup_{timestamp}.json"
        shutil.copy(CATALOG_JSON_PATH, backup_path)

    with open(CATALOG_JSON_PATH, 'w') as f:
        json.dump(catalog, f, indent=2)
    print(f"  [CATALOG] Saved: {CATALOG_JSON_PATH}")


def create_song_entry(metadata: Dict[str, Any], r2_path: str) -> Dict[str, Any]:
    """Create a new song entry for the catalog."""
    now = datetime.now().isoformat()

    return {
        "song_id": generate_song_id(),
        "title": metadata["title"],
        "alt_titles": [],
        "act_id": get_act_id(metadata["artist"]),
        "artist": metadata["artist"],
        "album": metadata.get("album", "Unknown Album"),
        "writers": [],
        "legacy_code": "",
        "musical_info": {
            "genre": metadata.get("genre") or "Unknown",
            "subgenre": "",
            "bpm": metadata.get("bpm"),
            "key": None,
            "time_signature": "4/4",
            "duration_seconds": metadata.get("duration_seconds"),
            "instrumental": False
        },
        "sync_metadata": {
            "moods": [],
            "themes": [],
            "keywords": [],
            "similar_artists": [],
            "use_cases": [],
            "explicit": False,
            "one_stop": True
        },
        "status": "finished",
        "dates": {
            "created": now,
            "demo_completed": now,
            "mastered": now,
            "released": None,
            "last_modified": now
        },
        "registration": {
            "isrc": None,
            "iswc": None,
            "pro_work_id": None,
            "copyright_reg": None,
            "registered_with": []
        },
        "rights": {
            "master_owner": "Ridgemont Studio",
            "publisher": "Ridgemont Studio",
            "territories": ["Worldwide"],
            "restrictions": [],
            "licenses": []
        },
        "revenue": {
            "expenses": [],
            "total_earned": 0
        },
        "links": {
            "r2_path": r2_path
        },
        "events": [
            {
                "timestamp": now,
                "event_type": "created",
                "description": f"Auto-uploaded via watch_and_upload.py",
                "user": "System"
            }
        ],
        "notes": "",
        "sync_checklist": {
            "sync_status": "available",
            "master_cleared": True,
            "publishing_cleared": True,
            "one_stop_available": True,
            "stems_available": False,
            "instrumental_available": False,
            "sync_rep_assigned": None,
            "pitch_deck_ready": False
        },
        "deployments": {
            "distribution": [],
            "sync_libraries": [],
            "streaming": []
        }
    }


# =============================================================================
# TRACKS.JSON FOR WEBSITE
# =============================================================================

def update_tracks_json(r2_client: R2Client, catalog: Dict[str, Any]) -> None:
    """Update the tracks.json file in R2 for the website."""

    # Get all finished songs with R2 paths
    tracks = []
    for song in catalog.get("songs", []):
        r2_path = song.get("links", {}).get("r2_path")
        if r2_path and song.get("status") in ["finished", "released"]:
            tracks.append({
                "id": song["song_id"],
                "file": r2_path,
                "title": song["title"],
                "artist": song.get("artist", "Unknown"),
                "album": song.get("album", "Unknown Album"),
                "duration": format_duration(song.get("musical_info", {}).get("duration_seconds")),
                "year": song.get("dates", {}).get("created", "")[:4] if song.get("dates", {}).get("created") else None,
                "genre": song.get("musical_info", {}).get("genre", "")
            })

    tracks_data = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "tracks": tracks
    }

    r2_client.upload_json(tracks_data, "tracks.json")


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds to M:SS format."""
    if not seconds:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


# =============================================================================
# FILE PROCESSOR
# =============================================================================

def process_file(file_path: Path, r2_client: R2Client) -> bool:
    """Process a single audio file: extract, upload, catalog, cleanup."""

    print(f"\n{'='*60}")
    print(f"Processing: {file_path.name}")
    print(f"{'='*60}")

    # 1. Extract metadata
    print("\n[1/5] Extracting metadata...")
    metadata = extract_metadata(file_path)
    print(f"  Title:    {metadata['title']}")
    print(f"  Artist:   {metadata['artist']}")
    print(f"  Album:    {metadata['album']}")
    print(f"  Duration: {format_duration(metadata['duration_seconds'])}")
    if metadata['genre']:
        print(f"  Genre:    {metadata['genre']}")

    # 2. Build R2 path
    print("\n[2/5] Building R2 path...")
    artist_folder = sanitize_filename(metadata['artist'])
    album_folder = sanitize_filename(metadata['album'])
    filename = sanitize_filename(metadata['title']) + file_path.suffix.lower()

    r2_key = f"{artist_folder}/{album_folder}/{filename}"

    # Handle duplicates
    if r2_client.file_exists(r2_key):
        timestamp = datetime.now().strftime("%Y%m%d")
        base_name = sanitize_filename(metadata['title'])
        filename = f"{base_name}-{timestamp}{file_path.suffix.lower()}"
        r2_key = f"{artist_folder}/{album_folder}/{filename}"
        print(f"  [DUPLICATE] Renamed to: {filename}")

    print(f"  R2 Path: {r2_key}")

    # 3. Upload to R2
    print("\n[3/5] Uploading to R2...")
    content_type = 'audio/mpeg' if file_path.suffix.lower() == '.mp3' else 'audio/wav'
    if not r2_client.upload_file(file_path, r2_key, content_type):
        print("  [ERROR] Upload failed!")
        return False

    # 4. Update catalog
    print("\n[4/5] Updating catalog...")
    catalog = load_catalog()
    song_entry = create_song_entry(metadata, r2_key)
    catalog["songs"].append(song_entry)
    save_catalog(catalog)
    print(f"  Song ID: {song_entry['song_id']}")
    print(f"  Act ID:  {song_entry['act_id']}")

    # Update tracks.json for website
    update_tracks_json(r2_client, catalog)

    # 5. Move to Completed folder
    print("\n[5/5] Moving to Completed...")
    COMPLETED_FOLDER.mkdir(parents=True, exist_ok=True)
    completed_path = COMPLETED_FOLDER / file_path.name

    # Handle duplicate in Completed folder
    if completed_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        completed_path = COMPLETED_FOLDER / f"{file_path.stem}_{timestamp}{file_path.suffix}"

    shutil.move(str(file_path), str(completed_path))
    print(f"  Moved to: {completed_path}")

    print(f"\n[SUCCESS] {metadata['title']} uploaded successfully!")
    return True


# =============================================================================
# FOLDER WATCHER
# =============================================================================

class UploadHandler(FileSystemEventHandler):
    """Watches for new audio files and processes them."""

    def __init__(self, r2_client: R2Client):
        self.r2_client = r2_client
        self.processing = set()  # Track files being processed

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Skip non-audio files
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        # Skip files in Completed folder
        if "Completed" in str(file_path):
            return

        # Skip if already processing
        if str(file_path) in self.processing:
            return

        self.processing.add(str(file_path))

        try:
            # Wait a moment for file to finish writing
            time.sleep(2)

            # Verify file still exists and is complete
            if not file_path.exists():
                return

            # Check file is not still being written
            initial_size = file_path.stat().st_size
            time.sleep(1)
            if file_path.exists() and file_path.stat().st_size != initial_size:
                time.sleep(3)  # Wait longer if still changing

            process_file(file_path, self.r2_client)

        except Exception as e:
            print(f"\n[ERROR] Failed to process {file_path.name}: {e}")

        finally:
            self.processing.discard(str(file_path))


def watch_folder(r2_client: R2Client) -> None:
    """Start watching the upload folder."""

    # Ensure watch folder exists
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    COMPLETED_FOLDER.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("RIDGEMONT CATALOG MANAGER - Watch & Upload")
    print(f"{'='*60}")
    print(f"\nWatching folder: {WATCH_FOLDER}")
    print(f"Completed folder: {COMPLETED_FOLDER}")
    print(f"Catalog: {CATALOG_JSON_PATH}")
    print(f"\nDrop .mp3 or .wav files into the watch folder to upload.")
    print("Press Ctrl+C to stop.\n")

    # Process any existing files first
    existing_files = list(WATCH_FOLDER.glob("*.mp3")) + list(WATCH_FOLDER.glob("*.wav"))
    if existing_files:
        print(f"Found {len(existing_files)} existing file(s) to process...\n")
        for file_path in existing_files:
            if "Completed" not in str(file_path):
                process_file(file_path, r2_client)

    # Start watching
    event_handler = UploadHandler(r2_client)
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        observer.stop()

    observer.join()
    print("Goodbye!")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""

    # Verify .env exists
    env_path = CATALOG_MANAGER_ROOT / ".env"
    if not env_path.exists():
        print("ERROR: .env file not found!")
        print(f"Please create: {env_path}")
        print("\nRequired variables:")
        print("  CLOUDFLARE_ACCOUNT_ID=your_account_id")
        print("  CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key")
        print("  CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key")
        print("  R2_BUCKET_NAME=ridgemont-studio")
        sys.exit(1)

    # Initialize R2 client
    try:
        r2_client = R2Client()
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Start watching
    watch_folder(r2_client)


if __name__ == "__main__":
    main()
