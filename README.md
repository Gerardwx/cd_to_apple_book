# cd_to_apple_book
Personal CD to Apple Books audiobook pipeline.

## Overview

This package provides two programs for converting audiobook CDs into Apple Books-compatible m4b files:

1. **ripper** (Linux) - Rips audio CDs to m4a files
2. **importer** (macOS) - Combines m4a files into a single m4b audiobook and imports to Books

## Workflow

1. Create a YAML configuration file (e.g., `contract.yaml`) describing your audiobook
2. Run `ripper` on Linux to rip all CDs
3. Run `importer` on macOS to create and import the m4b audiobook

**Note:** The programs can share files via:
- A shared NFS drive (set `rip path` and `import path` to the same NFS location)
- Manual file transfer between systems

## Configuration File

Create a YAML file with the following structure:

```yaml
title: "Book Title"
author: "Author Name"
narrator: "Narrator Name"
cds: 5
rip path: ~/audiobooks/rips
import path: ~/audiobooks/rips
audio:
  codec: aac
  bitrate: 128k
  channels: mono
```

Required fields:
- `title`: Audiobook title
- `cds`: Number of discs

Optional fields:
- `author`: Book author (used in metadata)
- `narrator`: Audiobook narrator (used in metadata)
- `rip path`: Where to save ripped files (default: current directory)
- `import path`: Where to find ripped files for import
- `audio`: Audio encoding settings
  - `codec`: Audio codec (default: aac)
  - `bitrate`: Encoding bitrate (e.g., 128k, 192k)
  - `channels`: mono or stereo

## Ripper (Linux)

Rips audiobook CDs using `abcde` and creates organized directories with m4a files.

**Requirements:**
- Linux system
- `abcde` installed
- CD drive

**Usage:**

```bash
ripper contract.yaml
```

**Options:**
- `--start-disc N`: Resume from disc N (useful if interrupted)
- `--paranoid`: Use full error correction (slow but safest)
- `--relaxed`: Faster ripping with fewer retries (default)
- `--dry-run`: Show what would be done without actually ripping

**Output:**

Creates a directory structure:
```
~/audiobooks/rips/Book_Title/
├── book.yaml
├── disc1/
│   ├── 01.track.m4a
│   ├── 02.track.m4a
│   └── ...
├── disc2/
│   └── ...
```

**Features:**
- Automatic MusicBrainz lookup with fallback
- Tracks ripping time per disc
- Skips already-ripped discs
- Configurable audio encoding via YAML

## Importer (macOS)

Combines ripped m4a files into a single m4b audiobook and imports to Apple Books.

**Requirements:**
- macOS
- `ffmpeg` and `ffprobe` installed
- Ripped files from ripper

**Usage:**

```bash
importer contract.yaml
```

**Features:**
- Automatically concatenates all tracks in disc/track order
- Creates chapter markers for each track (labeled "Disc X · Track Y")
- Adds metadata from YAML (title, author, narrator, genre)
- Validates all expected discs are present
- Opens finished m4b in Apple Books

**Output:**

Creates `Book_Title.m4b` in the book directory and automatically imports it to Books.

