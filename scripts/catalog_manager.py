#!/usr/bin/env python3
"""
Ridgemont Catalog Manager - Core Module
Version: 5.2 (Phase 5C - Pitch Perfect)
Author: Claude (for John York / Ridgemont Studio)
Date: January 24, 2026
Updates in v5.2:
- Pitch Engine: > Pitch "Song" "Supervisor" command.
- Email Drafter: Auto-generates subject lines and body text based on song mood.
- Pitch Logging: Automatically records the pitch in supervisors.json.
"""
import json
import os
import re
import csv
import glob
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from collections import defaultdict
# ============================================================================
# CONFIGURATION
# ============================================================================
# USER CONFIGURATION
# The absolute path on John York's Mac
USER_MAC_ROOT = Path("/Users/johnyork/My Drive/Ridgemont Studio/Claude Cowork/Ridgemont Catalog Manager")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
DASHBOARDS_DIR = BASE_DIR / "dashboards"
BACKUPS_DIR = BASE_DIR / "backups"
PITCH_DECKS_DIR = BASE_DIR / "pitch_decks"
ACT_IDS = { "FROZEN_CLOUD": "FROZEN_CLOUD", "FC": "FROZEN_CLOUD", "PARK_BELLEVUE": "PARK_BELLEVUE", "PB": "PARK_BELLEVUE", "BAJAN_SUN": "BAJAN_SUN", "BS": "BAJAN_SUN" }
DEFAULT_SPLITS = {
    "FROZEN_CLOUD": [{"writer_id": "W-0001", "percentage": 50}, {"writer_id": "W-0002", "percentage": 50}],
    "PARK_BELLEVUE": [{"writer_id": "W-0001", "percentage": 50}, {"writer_id": "W-0003", "percentage": 50}],
    "BAJAN_SUN": [{"writer_id": "W-0001", "percentage": 100}],
}
# ============================================================================
# CATALOG MANAGER CLASS
# ============================================================================
class CatalogManager:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.catalog = {"songs": []}
        self.supervisors = {"supervisors": []}
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        PITCH_DECKS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_data()
    def _load_data(self):
        files = ["catalog.json", "writers.json", "acts.json", "supervisors.json", "integrations.json"]
        for filename in files:
            p = self.data_dir / filename
            if p.exists():
                attr = filename.replace(".json", "")
                if attr == "catalog": attr = "catalog"
                with open(p, 'r') as f: setattr(self, attr, json.load(f))
        if not hasattr(self, 'catalog'): self.catalog = {"songs": []}
        if not hasattr(self, 'supervisors'): self.supervisors = {"supervisors": []}
    def _backup_data(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"catalog_backup_{timestamp}.json"
        with open(backup_path, 'w') as f: json.dump(self.catalog, f, indent=2, default=str)
        print(f"📦 Backup created: {backup_path.name}")
        backups = sorted(glob.glob(str(BACKUPS_DIR / "catalog_backup_*.json")))
        while len(backups) > 10: os.remove(backups.pop(0))
        return str(backup_path)
    def save_data(self):
        try: self._backup_data()
        except: pass
        data_map = {"catalog.json": self.catalog, "supervisors.json": self.supervisors}
        for filename, data in data_map.items():
            with open(self.data_dir / filename, 'w') as f: json.dump(data, f, indent=2, default=str)
        print(f"✅ Data saved to {self.data_dir}")
    # ========================================================================
    # PHASE 5C: THE PITCH ENGINE (Shortcodes)
    # ========================================================================
    def process_shortcode(self, command: str) -> str:
        """
        > Pitch "Song" "Supervisor"
        > Cost "Song" 150 Category
        > Forecast "Song" 1m
        """
        parts = [p.strip() for p in re.split(r'\s+', command.strip()) if p.strip()]
        if not parts or parts[0] != '>': return "Invalid command."

        cmd = parts[1].lower() if len(parts) > 1 else ""
        # > PITCH "Song" "Supervisor"
        if cmd == "pitch":
            match = re.search(r'Pitch "(.*?)" "(.*?)"', command, re.IGNORECASE)
            if not match: return "Format: > Pitch \"Song Title\" \"Supervisor Name\""
            title, supervisor_name = match.groups()
            return self.execute_pitch_shortcode(title, supervisor_name)
        # > COST / FORECAST / NEW / LIST (Preserved from v5.1)
        if cmd == "forecast":
            match = re.search(r'Forecast "(.*?)" ([\d\.]+[km]?)', command, re.IGNORECASE)
            if not match: return "Format: > Forecast \"Title\" 1m"
            return self.simulate_royalties(match.group(1), match.group(2))
        if cmd == "cost":
            match = re.search(r'Cost "(.*?)" ([\d\.]+) (.*)', command, re.IGNORECASE)
            if not match: return "Format: > Cost \"Title\" 150 Category"
            return self.add_expense_shortcode(match.group(1), float(match.group(2)), match.group(3))
        if cmd == "sync": return "Excel Sync Stub Executed."
        if cmd == "backup": return f"Backup: {self._backup_data()}"
        # > FC New / List
        act_key = parts[1].upper()
        act_id = ACT_IDS.get(act_key)
        if not act_id: return f"Unknown Act: {parts[1]}"
        action = parts[2].lower()

        if action == "new":
            # Parse: > FC New "Title" CODE Status
            # or:    > FC New "Title" Status
            match = re.search(r'New "(.*?)"', command, re.IGNORECASE)
            title = match.group(1) if match else "Untitled"

            # Extract remaining parts after title
            after_title = command[match.end():].strip().split() if match else parts[3:]

            legacy_code = None
            status = "idea"

            for part in after_title:
                part_clean = part.strip()
                # Check if it's a 4-letter code (all caps)
                if len(part_clean) == 4 and part_clean.isupper() and part_clean.isalpha():
                    legacy_code = part_clean
                # Check if it's a status
                elif part_clean.lower() in ["idea", "demo", "mixing", "mastered", "copyright", "released"]:
                    status = part_clean.lower()

            result = self.add_song(title, act_id, status=status, legacy_code=legacy_code)

            # Check if result is an error string
            if isinstance(result, str) and result.startswith("❌"):
                return result

            code_msg = f" (Code: {legacy_code})" if legacy_code else ""
            return f"✅ Added '{title}' to {act_id}{code_msg}"

        if action == "list":
            songs = [s for s in self.catalog['songs'] if s['act_id'] == act_id]
            return self.format_results_table(songs[:10])
        return "Unknown command."
    # ========================================================================
    # PITCH LOGIC
    # ========================================================================
    def execute_pitch_shortcode(self, song_title: str, supervisor_name: str) -> str:
        # 1. Find Song
        song = self.find_song_by_title(song_title)
        if not song: return f"Error: Song '{song_title}' not found."
        # 2. Find/Create Supervisor
        supervisor = next((s for s in self.supervisors["supervisors"] if s["name"].lower() == supervisor_name.lower()), None)
        if not supervisor:
            supervisor = {"id": f"SUP-{datetime.now().strftime('%M%S')}", "name": supervisor_name, "email": "TBD", "history": []}
            self.supervisors["supervisors"].append(supervisor)
            new_sup_msg = "(New Contact Created)"
        else:
            new_sup_msg = ""
        # 3. Log Pitch
        pitch_entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "song": song["title"],
            "project": "General Pitch"
        }
        if "history" not in supervisor: supervisor["history"] = []
        supervisor["history"].append(pitch_entry)
        self.save_data()
        # 4. Generate HTML Page
        html_path = self.generate_pitch_html(song, supervisor)
        # 5. Draft Email
        mood = (song.get("sync_metadata", {}).get("moods", ["Energy"]) or ["Energy"])[0]
        act = song["act_id"].replace("_", " ").title()

        email_subject = f"🎵 {mood} Track for your consideration: \"{song['title']}\""
        email_body = (
            f"Hi {supervisor_name.split()[0]},\n\n"
            f"Knowing you often look for {mood.lower()} tracks, I wanted to share \"{song['title']}\" from my project {act}.\n\n"
            f"It's a {song.get('status', 'mastered')} track perfect for driving/montage scenes.\n\n"
            f"LISTEN HERE: [Link to Stream]\n"
            f"METADATA: One-Stop | {song.get('musical_info', {}).get('bpm', 'N/A')} BPM | {act}\n\n"
            f"Best,\nJohn York\nRidgemont Studio"
        )
        return (
            f"🚀 **Pitch Generated for {supervisor_name}** {new_sup_msg}\n"
            f"---------------------------------------------------\n"
            f"**To:** {supervisor_name} <{supervisor.get('email', 'email@example.com')}>\n"
            f"**Subject:** {email_subject}\n\n"
            f"{email_body}\n"
            f"---------------------------------------------------\n"
            f"📄 **Pitch Page:** {html_path}\n"
            f"✅ **Logged:** Added to supervisor history."
        )
    def generate_pitch_html(self, song: Dict, supervisor: Dict) -> str:
        filename = f"pitch_{song['song_id']}_{supervisor['name'].replace(' ', '')}.html"
        path = PITCH_DECKS_DIR / filename
        html = f"""<html><body style="font-family:sans-serif; padding:40px; background:#f4f4f4;">
        <div style="max-width:600px; margin:auto; background:white; padding:30px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color:#333;">{song['title']}</h1>
            <p style="color:#666;">Prepared exclusively for <strong>{supervisor['name']}</strong></p>
            <hr>
            <p><strong>Artist:</strong> {song['act_id'].replace('_', ' ')}</p>
            <p><strong>BPM:</strong> {song.get('musical_info', {}).get('bpm', 'N/A')}</p>
            <p><strong>Moods:</strong> {', '.join(song.get('sync_metadata', {}).get('moods', []))}</p>
            <div style="background:#e8f0fe; padding:15px; border-radius:5px; margin-top:20px;">
                <strong>✅ Sync Status:</strong> One-Stop | Mastered | Stems Available
            </div>
            <p style="margin-top:30px; font-size:12px; color:#999;">&copy; 2026 Ridgemont Studio</p>
        </div></body></html>"""
        with open(path, 'w') as f: f.write(html)
        # FIX: Return user's Mac path for clickable links
        user_path = USER_MAC_ROOT / "pitch_decks" / filename
        return user_path.as_uri()
    def generate_dashboard_html(self, output_path: str = None, include_charts: bool = True) -> str:
        if output_path is None:
            DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = DASHBOARDS_DIR / f"dashboard_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.html"

        summary = self.get_catalog_summary()
        revenue = self.get_revenue_summary()

        html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Ridgemont Studio</title>
        <style>body{{font-family:sans-serif;padding:20px;background:#1a1a2e;color:#fff}}h1{{color:#64ffda}}.stat{{background:rgba(255,255,255,0.05);padding:20px;border-radius:10px;margin:10px 0}}</style>
        </head><body><h1>🎵 Ridgemont Studio Dashboard</h1>
        <div class="stat"><h3>Total Songs</h3><p style="font-size:2rem;color:#64ffda">{summary['total_songs']}</p></div>
        <div class="stat"><h3>Total Revenue</h3><p style="font-size:2rem;color:#ffd700">${revenue['total_revenue']:,.2f}</p></div>
        <p style="color:#666">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </body></html>"""

        with open(output_path, 'w') as f: f.write(html)
        # FIX: Return user's Mac path for clickable links
        filename = Path(output_path).name
        user_path = USER_MAC_ROOT / "dashboards" / filename
        return user_path.as_uri()
    def get_catalog_summary(self) -> Dict:
        songs = self.catalog.get("songs", [])
        by_act = {}
        by_status = {}
        for s in songs:
            act = s.get('act_id', 'Unknown')
            status = s.get('status', 'unknown')
            by_act[act] = by_act.get(act, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
        return {"total_songs": len(songs), "by_act": by_act, "by_status": by_status}
    def get_revenue_summary(self) -> Dict:
        total = sum(s.get("revenue", {}).get("total_earned", 0) for s in self.catalog.get("songs", []))
        return {"total_revenue": total, "sync_income": 0, "top_earners": []}
    # ========================================================================
    # HELPERS (Preserved from v5.1)
    # ========================================================================
    def find_song_by_title(self, title: str) -> Optional[Dict]:
        for s in self.catalog["songs"]:
            if s["title"].lower() == title.lower(): return s
        return None
    def find_song_by_code(self, code: str) -> Optional[Dict]:
        """Find a song by its 4-letter legacy code."""
        code_upper = code.upper().strip()
        for s in self.catalog["songs"]:
            if s.get("legacy_code", "").upper() == code_upper:
                return s
        return None
    def is_code_unique(self, code: str) -> bool:
        """Check if a 4-letter code is unique (not already used)."""
        return self.find_song_by_code(code) is None
    def generate_unique_code(self, title: str) -> str:
        """Auto-generate a unique 4-letter code from the song title."""
        # Remove special characters and get uppercase letters
        clean_title = ''.join(c for c in title.upper() if c.isalpha())

        # Strategy 1: First 4 letters of title
        if len(clean_title) >= 4:
            candidate = clean_title[:4]
            if self.is_code_unique(candidate):
                return candidate

        # Strategy 2: First letters of each word
        words = [w for w in title.upper().split() if w and w[0].isalpha()]
        if len(words) >= 4:
            candidate = ''.join(w[0] for w in words[:4])
            if self.is_code_unique(candidate):
                return candidate
        elif len(words) >= 2:
            # Pad with letters from first word
            candidate = ''.join(w[0] for w in words)
            remaining = 4 - len(candidate)
            if len(clean_title) > len(words):
                candidate += clean_title[len(words):len(words)+remaining]
            candidate = candidate[:4].ljust(4, 'X')
            if self.is_code_unique(candidate):
                return candidate

        # Strategy 3: Try variations with numbers converted to letters
        base = clean_title[:3] if len(clean_title) >= 3 else clean_title.ljust(3, 'X')
        for suffix in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            candidate = base[:3] + suffix
            if self.is_code_unique(candidate):
                return candidate

        # Strategy 4: Fallback with timestamp
        import random
        for _ in range(100):
            candidate = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))
            if self.is_code_unique(candidate):
                return candidate

        return None  # Should never happen
    def add_song(self, title: str, act_id: str, status: str = "idea", legacy_code: str = None, is_cover: bool = False, cover_of: str = None, artist: str = None, deployments: dict = None):
        """Add a new song with deployment tracking. Auto-generates unique 4-letter code and Song ID."""
        # For cover songs, use the same code as the original song
        if is_cover and cover_of:
            original_song = self.find_song_by_title(cover_of)
            if original_song and original_song.get('legacy_code'):
                legacy_code = original_song['legacy_code']
            else:
                # If original not found, generate new code
                legacy_code = self.generate_unique_code(title)
        elif legacy_code:
            legacy_code = legacy_code.upper().strip()
            if len(legacy_code) != 4:
                return f"❌ Error: Code must be exactly 4 characters. Got: '{legacy_code}'"
            if not self.is_code_unique(legacy_code):
                existing = self.find_song_by_code(legacy_code)
                return f"❌ Error: Code '{legacy_code}' already used by '{existing['title']}'"
        else:
            # Auto-generate code for original songs
            legacy_code = self.generate_unique_code(title)
            if not legacy_code:
                return f"❌ Error: Could not generate unique code for '{title}'"

        writers = DEFAULT_SPLITS.get(act_id, DEFAULT_SPLITS["FROZEN_CLOUD"])
        year = str(datetime.now().year)
        count = sum(1 for s in self.catalog["songs"] if s["song_id"].startswith(f"RS-{year}"))
        song_id = f"RS-{year}-{count + 1:04d}"
        # Determine artist name (default to act name if not provided)
        if not artist:
            artist_map = {
                "FROZEN_CLOUD": "Frozen Cloud",
                "PARK_BELLEVUE": "Park Bellevue",
                "BAJAN_SUN": "Bajan Sun"
            }
            artist = artist_map.get(act_id, "Unknown")

        song = {
            "song_id": song_id,
            "title": title,
            "artist": artist,
            "act_id": act_id,
            "writers": writers,
            "status": status,
            "legacy_code": legacy_code or "",
            "deployments": deployments or {
                "distribution": [],      # e.g., DistroKid, TuneCore, CD Baby
                "sync_libraries": [],    # e.g., Songtradr, Music Gateway, Pond5
                "streaming": []          # e.g., Spotify, Apple Music, Amazon
            },
            "revenue": {"expenses": [], "total_earned": 0},
            "dates": {"created": datetime.now().strftime("%Y-%m-%d")}
        }
        # Add cover info if applicable
        if is_cover and cover_of:
            song["is_cover"] = True
            song["cover_of"] = cover_of
        self.catalog["songs"].append(song)
        self.save_data()
        return song
    def update_song(self, song_id: str, updates: dict) -> bool:
        """Updates an existing song's details (status, deployments, ISRC, ISWC, etc.)."""
        for song in self.catalog['songs']:
            if song['song_id'] == song_id:
                # Handle nested updates for registration info (ISRC, ISWC, etc.)
                if 'registration' in updates:
                    if 'registration' not in song:
                        song['registration'] = {}
                    song['registration'].update(updates.pop('registration'))

                # Handle nested updates for deployments
                if 'deployments' in updates:
                    if 'deployments' not in song:
                        song['deployments'] = {"distribution": [], "sync_libraries": [], "streaming": []}
                    song['deployments'].update(updates.pop('deployments'))

                # Apply remaining updates
                song.update(updates)

                # Update timestamp
                if 'dates' not in song:
                    song['dates'] = {}
                song['dates']['last_modified'] = datetime.now().isoformat()

                self.save_data()
                return True
        return False

    def add_expense_shortcode(self, title: str, amount: float, category: str) -> str:
        song = self.find_song_by_title(title)
        if not song: return "Song not found."
        if "revenue" not in song: song["revenue"] = {}
        if "expenses" not in song["revenue"]: song["revenue"]["expenses"] = []
        song["revenue"]["expenses"].append({"date": datetime.now().strftime("%Y-%m-%d"), "amount": amount, "category": category})
        self.save_data()
        return f"💸 Logged ${amount} for {title}."
    def simulate_royalties(self, title: str, amount_str: str) -> str:
        song = self.find_song_by_title(title)
        if not song: return "Song not found."
        multiplier = 1_000_000 if 'm' in amount_str.lower() else 1_000
        count = float(amount_str.lower().rstrip('mk')) * multiplier
        rev = count * 0.004
        return f"🔮 Forecast ({amount_str}): ${rev:,.2f}"
    def format_results_table(self, songs: List[Dict]) -> str:
        if not songs: return "No songs."
        rows = [f"| {s['title']} | {s['status']} |" for s in songs]
        return "\n".join(["| Title | Status |", "|---|---|"] + rows)
if __name__ == "__main__":
    print("Ridgemont Catalog Manager v5.2 Loaded")
