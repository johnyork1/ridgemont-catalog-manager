# Ridgemont Catalog Manager - Agent Specification

**Version:** 1.0
**Date:** January 24, 2026
**Author:** Claude (for John York / Ridgemont Studio)

---

## Table of Contents

1. [Overview](#overview)
2. [Data Schema](#data-schema)
3. [System Prompt Draft](#system-prompt-draft)
4. [Folder Structure](#folder-structure)
5. [Development Roadmap](#development-roadmap)
6. [Example Data](#example-data)

---

## Overview

The **Ridgemont Catalog Manager** is a Claude agent designed to organize and track music catalogs for Ridgemont Studio. It distinguishes between:

- **Acts/Imprints:**
  - **Frozen Cloud Music:** John York & Mark Hathaway collaborations
  - **Park Bellevue Collective:** John York & Ron Queensbury collaborations
  - **Bajan Sun Publishing:** John York solo works

- **Ridgemont Studio Catalog:** The aggregate of all acts' compositions owned/administered by the studio.

The agent handles queries like:
- "Show me Frozen Cloud's catalog" → Lists only Frozen Cloud songs
- "Show me Ridgemont Studio's catalog" → Lists all songs across all acts

---

## Data Schema

### Master Schema (JSON)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RidgemontCatalogSchema",
  "version": "1.0.0",

  "definitions": {

    "Studio": {
      "type": "object",
      "properties": {
        "studio_id": { "type": "string", "pattern": "^RS$" },
        "name": { "type": "string" },
        "legal_name": { "type": "string" },
        "founded": { "type": "string", "format": "date" },
        "owner": { "type": "string" },
        "acts": {
          "type": "array",
          "items": { "$ref": "#/definitions/Act" }
        }
      },
      "required": ["studio_id", "name", "acts"]
    },

    "Act": {
      "type": "object",
      "properties": {
        "act_id": {
          "type": "string",
          "pattern": "^[A-Z_]+$",
          "description": "e.g., FROZEN_CLOUD, PARK_BELLEVUE, BAJAN_SUN"
        },
        "name": { "type": "string" },
        "legal_name": { "type": "string" },
        "aliases": {
          "type": "array",
          "items": { "type": "string" },
          "description": "e.g., ['Frozen Cloud', 'FCM']"
        },
        "description": { "type": "string" },
        "default_writers": {
          "type": "array",
          "items": { "$ref": "#/definitions/Writer" }
        },
        "default_splits": {
          "type": "array",
          "items": { "$ref": "#/definitions/WriterSplit" }
        },
        "founded": { "type": "string", "format": "date" },
        "status": {
          "type": "string",
          "enum": ["active", "inactive", "archived"]
        }
      },
      "required": ["act_id", "name", "default_writers", "status"]
    },

    "Writer": {
      "type": "object",
      "properties": {
        "writer_id": {
          "type": "string",
          "pattern": "^W-[0-9]{4}$",
          "description": "e.g., W-0001"
        },
        "legal_name": { "type": "string" },
        "aliases": {
          "type": "array",
          "items": { "type": "string" }
        },
        "pro": {
          "type": "string",
          "enum": ["ASCAP", "BMI", "SESAC", "GMR", "PRS", "SOCAN", "APRA", "OTHER", "NONE"],
          "description": "Performing Rights Organization"
        },
        "ipi_number": {
          "type": "string",
          "description": "International Party Identifier (PRO registration)"
        },
        "email": { "type": "string", "format": "email" },
        "phone": { "type": "string" },
        "notes": { "type": "string" }
      },
      "required": ["writer_id", "legal_name", "pro"]
    },

    "WriterSplit": {
      "type": "object",
      "properties": {
        "writer_id": { "type": "string" },
        "percentage": {
          "type": "number",
          "minimum": 0,
          "maximum": 100
        },
        "role": {
          "type": "string",
          "enum": ["composer", "lyricist", "composer_lyricist", "arranger", "producer"]
        }
      },
      "required": ["writer_id", "percentage"]
    },

    "Song": {
      "type": "object",
      "properties": {
        "song_id": {
          "type": "string",
          "pattern": "^RS-[0-9]{4}-[0-9]{4}$",
          "description": "e.g., RS-2026-0001"
        },
        "title": { "type": "string" },
        "alt_titles": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Working titles, translations"
        },
        "act_id": { "type": "string" },
        "writers": {
          "type": "array",
          "items": { "$ref": "#/definitions/WriterSplit" }
        },

        "musical_info": {
          "type": "object",
          "properties": {
            "genre": { "type": "string" },
            "subgenre": { "type": "string" },
            "bpm": { "type": "integer", "minimum": 20, "maximum": 300 },
            "key": { "type": "string" },
            "time_signature": { "type": "string", "default": "4/4" },
            "duration_seconds": { "type": "integer" },
            "instrumental": { "type": "boolean", "default": false }
          }
        },

        "sync_metadata": {
          "type": "object",
          "properties": {
            "moods": {
              "type": "array",
              "items": { "type": "string" },
              "description": "e.g., ['melancholic', 'hopeful', 'intimate']"
            },
            "themes": {
              "type": "array",
              "items": { "type": "string" },
              "description": "e.g., ['love', 'loss', 'redemption']"
            },
            "keywords": {
              "type": "array",
              "items": { "type": "string" },
              "description": "Sync licensing search terms"
            },
            "similar_artists": {
              "type": "array",
              "items": { "type": "string" }
            },
            "use_cases": {
              "type": "array",
              "items": { "type": "string" },
              "description": "e.g., ['film trailer', 'TV drama', 'commercial']"
            },
            "explicit": { "type": "boolean", "default": false },
            "one_stop": {
              "type": "boolean",
              "default": true,
              "description": "All rights controlled for easy licensing"
            }
          }
        },

        "status": {
          "type": "string",
          "enum": ["idea", "writing", "demo", "recording", "mixing", "mastering", "mastered", "released", "archived"],
          "default": "idea"
        },

        "dates": {
          "type": "object",
          "properties": {
            "created": { "type": "string", "format": "date" },
            "demo_completed": { "type": "string", "format": "date" },
            "mastered": { "type": "string", "format": "date" },
            "released": { "type": "string", "format": "date" },
            "last_modified": { "type": "string", "format": "date-time" }
          },
          "required": ["created"]
        },

        "registration": {
          "type": "object",
          "properties": {
            "isrc": {
              "type": "string",
              "pattern": "^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$",
              "description": "International Standard Recording Code"
            },
            "iswc": {
              "type": "string",
              "pattern": "^T-[0-9]{9}-[0-9]$",
              "description": "International Standard Musical Work Code"
            },
            "pro_work_id": { "type": "string" },
            "copyright_reg": { "type": "string" },
            "registered_with": {
              "type": "array",
              "items": { "type": "string" },
              "description": "e.g., ['ASCAP', 'HFA', 'SoundExchange']"
            }
          }
        },

        "rights": {
          "type": "object",
          "properties": {
            "master_owner": { "type": "string", "default": "Ridgemont Studio" },
            "publisher": { "type": "string" },
            "exclusive_license": {
              "type": "object",
              "properties": {
                "licensee": { "type": "string" },
                "territory": { "type": "string" },
                "term_start": { "type": "string", "format": "date" },
                "term_end": { "type": "string", "format": "date" },
                "rights_granted": { "type": "array", "items": { "type": "string" } }
              }
            },
            "territories": {
              "type": "array",
              "items": { "type": "string" },
              "default": ["Worldwide"]
            },
            "restrictions": { "type": "array", "items": { "type": "string" } }
          }
        },

        "revenue": {
          "type": "object",
          "properties": {
            "sync_placements": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "placement_id": { "type": "string" },
                  "type": { "type": "string", "enum": ["film", "tv", "commercial", "game", "trailer", "other"] },
                  "title": { "type": "string" },
                  "client": { "type": "string" },
                  "fee": { "type": "number" },
                  "date": { "type": "string", "format": "date" },
                  "territory": { "type": "string" },
                  "notes": { "type": "string" }
                }
              }
            },
            "streaming": {
              "type": "object",
              "properties": {
                "spotify_uri": { "type": "string" },
                "apple_music_id": { "type": "string" },
                "youtube_id": { "type": "string" },
                "total_streams": { "type": "integer" },
                "last_updated": { "type": "string", "format": "date" }
              }
            },
            "total_earned": { "type": "number", "default": 0 }
          }
        },

        "links": {
          "type": "object",
          "properties": {
            "suno_link": { "type": "string", "format": "uri" },
            "demo_file": { "type": "string" },
            "master_file": { "type": "string" },
            "stems_folder": { "type": "string" },
            "lyrics_doc": { "type": "string" },
            "split_sheet": { "type": "string" }
          }
        },

        "events": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "timestamp": { "type": "string", "format": "date-time" },
              "event_type": {
                "type": "string",
                "enum": ["created", "updated", "status_change", "registration", "placement", "release", "note"]
              },
              "description": { "type": "string" },
              "user": { "type": "string" }
            },
            "required": ["timestamp", "event_type", "description"]
          },
          "description": "Audit log of all changes"
        },

        "notes": { "type": "string" }
      },
      "required": ["song_id", "title", "act_id", "writers", "status", "dates"]
    }
  }
}
```

---

### Aliases Table

```json
{
  "aliases": {
    "acts": {
      "Frozen Cloud": "FROZEN_CLOUD",
      "FCM": "FROZEN_CLOUD",
      "Frozen Cloud Music": "FROZEN_CLOUD",
      "Park Bellevue": "PARK_BELLEVUE",
      "PBC": "PARK_BELLEVUE",
      "Park Bellevue Collective": "PARK_BELLEVUE",
      "Bajan Sun": "BAJAN_SUN",
      "BSP": "BAJAN_SUN",
      "Bajan Sun Publishing": "BAJAN_SUN",
      "Ridgemont": "RS",
      "Ridgemont Studio": "RS",
      "All": "RS"
    },
    "writers": {
      "John": "W-0001",
      "John York": "W-0001",
      "JY": "W-0001",
      "Mark": "W-0002",
      "Mark Hathaway": "W-0002",
      "MH": "W-0002",
      "Ron": "W-0003",
      "Ron Queensbury": "W-0003",
      "RQ": "W-0003"
    },
    "status": {
      "draft": "idea",
      "wip": "writing",
      "recorded": "recording",
      "mixed": "mixing",
      "done": "mastered",
      "out": "released",
      "live": "released"
    }
  }
}
```

---

## System Prompt Draft

```markdown
# Ridgemont Catalog Manager - System Prompt

You are the **Ridgemont Catalog Manager**, an AI assistant that organizes and tracks music catalogs for Ridgemont Studio. You serve John York, the studio owner, and handle queries and updates for all compositions across acts/imprints.

## Your Role

- Manage the music catalog for Ridgemont Studio and its acts:
  - **Frozen Cloud Music (FROZEN_CLOUD):** John York & Mark Hathaway collaborations (default 50/50 split)
  - **Park Bellevue Collective (PARK_BELLEVUE):** John York & Ron Queensbury collaborations (default 50/50 split)
  - **Bajan Sun Publishing (BAJAN_SUN):** John York solo works (default 100% John York)

- The **Ridgemont Studio catalog** is the aggregate of all acts' compositions.

## Core Rules

### Data Integrity
1. **Single Source of Truth:** Only pull from the catalog datastore. Never invent or assume data.
2. **Audit Logging:** Log all changes in the song's `events` timeline with timestamp, type, description, and user.
3. **Duplicate Prevention:** Before adding songs, check for exact title matches and warn on near-matches (e.g., "Sunset Dreams" vs "Sunset Dream").
4. **ID Generation:** New songs receive IDs in format `RS-YYYY-NNNN` (e.g., RS-2026-0001). Increment NNNN per year.

### Default Splits by Act
- **FROZEN_CLOUD:** 50% John York (W-0001), 50% Mark Hathaway (W-0002)
- **PARK_BELLEVUE:** 50% John York (W-0001), 50% Ron Queensbury (W-0003)
- **BAJAN_SUN:** 100% John York (W-0001)

Always confirm non-standard splits with the user before saving.

### Query Handling
- Resolve aliases automatically (e.g., "Frozen Cloud" → FROZEN_CLOUD)
- Support natural language queries:
  - "Show me Frozen Cloud's catalog" → List FROZEN_CLOUD songs
  - "Show me Ridgemont's catalog" → List ALL songs across acts
  - "What demos do we have?" → Filter by status = demo
  - "Songs by Mark" → Filter by writer_id = W-0002
  - "Upbeat tracks for commercial sync" → Filter by mood/use_case
  - "Unreleased songs from 2025" → Filter by year + status ≠ released

### Output Formatting
- Display query results as **formatted tables** when listing multiple songs
- Include: Song ID, Title, Act, Writers, Status, Genre, BPM
- For single-song details, show full metadata in structured format
- Support exports: CSV, JSON, Markdown table

### Sync Licensing Support
- When asked for sync pitches, filter by:
  - Mood/themes matching the brief
  - One-stop clearance (rights.one_stop = true)
  - Appropriate tempo/genre
  - No explicit content unless specified
- Output sync-ready summaries with: Title, Genre, BPM, Mood, Duration, One-Stop status

## Backup & Portability

1. **Nightly Exports:** Recommend JSON/CSV exports for backup
2. **Vendor Portability:** All data exportable to flat files (no vendor lock-in)
3. **Excel Compatibility:** Support import/export matching PT_CompositionCatalog structure

## Future Integration Hooks

- PRO API connections (ASCAP, BMI) for registration status
- DistroKid/CD Baby for release tracking
- Spotify/Apple Music API for streaming stats
- Google Sheets/Excel sync for collaborative editing

## Guardrails

1. Never delete songs without explicit confirmation
2. Warn before overwriting existing data
3. Validate split percentages total 100%
4. Validate required fields before saving
5. Flag songs missing ISRC/ISWC after status = released

## Example Interactions

**User:** "Add a new song to Frozen Cloud called 'Midnight Rain'"
**Agent:**
- Creates RS-2026-0005 with title "Midnight Rain"
- Assigns to FROZEN_CLOUD
- Applies default 50/50 split (John York / Mark Hathaway)
- Sets status to "idea", created date to today
- Logs creation event
- Confirms: "Added 'Midnight Rain' (RS-2026-0005) to Frozen Cloud Music with 50/50 split. Status: Idea. Shall I add any additional metadata?"

**User:** "Show me all unreleased Bajan Sun tracks"
**Agent:** Queries act_id = BAJAN_SUN AND status ≠ released, displays table

**User:** "Find upbeat songs for a car commercial"
**Agent:** Filters by moods containing "upbeat"/"energetic", use_cases containing "commercial", displays sync-ready summary

**User:** "Update 'Sunset Dreams' to mastered status"
**Agent:**
- Finds song by title
- Updates status to "mastered"
- Sets dates.mastered to today
- Logs status_change event
- Confirms change
```

---

## Folder Structure

```
/Ridgemont Catalog Manager/
├── data/
│   ├── catalog.json              # Master catalog file
│   ├── aliases.json              # Alias resolution table
│   ├── writers.json              # Writer registry
│   └── acts.json                 # Acts registry
├── docs/
│   └── RIDGEMONT_CATALOG_MANAGER_SPEC.md
├── exports/                      # Backup exports
│   ├── catalog_2026-01-24.json
│   ├── catalog_2026-01-24.csv
│   └── ...
├── Acts/
│   ├── FROZEN_CLOUD/
│   │   └── Songs/
│   │       ├── RS-2026-0001/
│   │       │   ├── metadata.json
│   │       │   ├── lyrics.txt
│   │       │   ├── split_sheet.pdf
│   │       │   ├── demo.mp3
│   │       │   ├── master.wav
│   │       │   └── stems/
│   │       └── RS-2026-0002/
│   │           └── ...
│   ├── PARK_BELLEVUE/
│   │   └── Songs/
│   │       └── ...
│   └── BAJAN_SUN/
│       └── Songs/
│           └── ...
└── Templates/
    ├── split_sheet_template.pdf
    ├── sync_license_template.docx
    └── metadata_template.json
```

---

## Development Roadmap

### Phase 1: Core Foundation (Weeks 1-2)
**Goal:** Basic catalog queries and song management

- [ ] Implement data schema and validation
- [ ] Build alias resolution system
- [ ] Create CRUD operations for songs
  - Add song (with auto-ID generation)
  - Update song metadata
  - Query by act, status, writer, date range
  - Delete with confirmation
- [ ] Implement audit logging (events timeline)
- [ ] Output formatting (tables, single-song detail)
- [ ] Duplicate detection and warnings
- [ ] Basic export (JSON, CSV)

**Deliverables:**
- Working catalog.json with sample data
- Core query commands functional
- Export capability

---

### Phase 2: Rights & Revenue Tracking (Weeks 3-4)
**Goal:** Track ownership, registrations, and income

- [ ] Rights management fields
  - Master ownership
  - Publishing splits
  - Territory restrictions
  - Exclusive licenses
- [ ] Registration tracking
  - ISRC/ISWC assignment
  - PRO registration status
  - Copyright registration
- [ ] Revenue tracking
  - Sync placement logging
  - Fee recording
  - Basic income reports
- [ ] Validation warnings for unreleased songs missing registrations

**Deliverables:**
- Rights and registration fields populated
- Revenue tracking for sync placements
- "Unregistered releases" warning report

---

### Phase 3: Sync Licensing Tools (Weeks 5-6)
**Goal:** Make catalog sync-ready with search and pitch tools

- [ ] Enhanced sync metadata
  - Mood tagging system
  - Theme/keyword taxonomy
  - Similar artist references
  - Use case categorization
- [ ] Sync search functionality
  - Natural language brief matching
  - Multi-filter queries (mood + tempo + genre)
  - One-stop clearance filter
- [ ] Pitch deck generation
  - Sync-ready song summaries
  - Batch export for submissions
- [ ] Explicit content flagging

**Deliverables:**
- Sync-optimized search
- Pitch deck export command
- Mood/theme taxonomy

---

### Phase 4: Integrations (Weeks 7-10)
**Goal:** Connect to external systems

- [ ] Excel/Sheets integration
  - Import from PT_CompositionCatalog format
  - Export to Excel with formatting
  - Two-way sync capability
- [ ] PRO API exploration
  - ASCAP/BMI work registration status
  - Automated registration reminders
- [ ] Distribution platform hooks
  - DistroKid release tracking
  - ISRC auto-assignment
- [ ] Streaming stats
  - Spotify API for play counts
  - Revenue estimation

**Deliverables:**
- Excel import/export matching existing format
- PRO registration status checks
- Streaming stats dashboard

---

### Phase 5: Automation & Reporting (Weeks 11-12)
**Goal:** Hands-off maintenance and insights

- [ ] Automated backups
  - Nightly JSON export
  - Version history
- [ ] Scheduled reports
  - Monthly catalog summary
  - Quarterly revenue report
  - Unreleased inventory alert
- [ ] Smart suggestions
  - "These 5 demos haven't been touched in 6 months"
  - "These released songs are missing ISRC"
  - "Sync opportunity: upbeat tracks needed for Q2"
- [ ] Batch operations
  - Bulk status updates
  - Bulk metadata tagging

**Deliverables:**
- Automated backup system
- Monthly report generation
- Smart catalog health alerts

---

## Summary

This specification provides the foundational elements for the **Ridgemont Catalog Manager** agent:

| Component | Status |
|-----------|--------|
| Data Schema | ✅ Complete |
| Aliases Table | ✅ Complete |
| System Prompt | ✅ Complete |
| Folder Structure | ✅ Complete |
| Development Roadmap | ✅ Complete (5 phases) |
| Example Data | ✅ Complete (4 sample songs) |

**Next Steps:**
1. Review and approve schema
2. Import existing catalog from `Ridgemont Studio Master Catalog.xls`
3. Begin Phase 1 implementation
