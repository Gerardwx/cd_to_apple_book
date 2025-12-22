from pathlib import Path
import argparse, subprocess, yaml, sys, re, tempfile

def disc_num(p: Path) -> int:
    for part in p.parts:
        if part.startswith("disc"):
            return int(part[4:])
    raise ValueError(f"Cannot determine disc number from {p}")

def track_num(p: Path) -> int:
    return int(p.stem.split(".", 1)[0])

def build_chapters(tracks):
    """
    Build ffmpeg chapter metadata: one chapter per track.
    """
    lines = [";FFMETADATA1"]
    cur = 0
    for i, t in enumerate(tracks, 1):
        dur = float(
            subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=nw=1:nk=1", t]
            ).strip()
        )
        start = int(cur * 1_000_000_000)
        end = int((cur + dur) * 1_000_000_000)
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000000000",
            f"START={start}",
            f"END={end}",
            f"title=Chapter {i}",
        ]
        cur += dur
    return "\n".join(lines)

def import_book(book_dir: Path):
    with open(book_dir / "book.yaml") as f:
        meta = yaml.safe_load(f)

    expected = set(range(1, meta["cds"] + 1))
    found = {disc_num(p) for p in book_dir.glob("disc*/**/*.m4a")}
    if expected != found:
        raise RuntimeError(f"Disc mismatch: expected={sorted(expected)}, found={sorted(found)}")

    tracks = sorted(
        book_dir.glob("disc*/**/*.m4a"),
        key=lambda p: (disc_num(p), track_num(p)),
    )
    if not tracks:
        raise RuntimeError("No audio tracks found")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        concat = td / "concat.txt"
        concat.write_text("\n".join(f"file '{t.resolve()}'" for t in tracks))

        chapters = td / "chapters.txt"
        chapters.write_text(build_chapters(tracks))

        m4b = book_dir / f"{meta['title']}.m4b"

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat,
            "-i", chapters, "-map_metadata", "1",
            "-c:a", "copy",
            "-metadata", f"title={meta['title']}",
            "-metadata", f"album={meta['title']}",
            "-metadata", f"album_artist={meta.get('author','')}",
            "-metadata", f"artist={meta.get('narrator','')}",
            "-metadata", "genre=Audiobook",
            m4b,
        ]

        subprocess.run(ffmpeg_cmd, check=True)

    # Import into Books (reliable method)
    subprocess.run(
        ["open", "-a", "Books", str(m4b.resolve())],
        check=True,
    )

    # Practical verification
    if not m4b.exists() or m4b.stat().st_size == 0:
        raise RuntimeError("Import failed: m4b not created correctly")

    print(f"Imported audiobook into Books: {m4b}")

def main():
    p = argparse.ArgumentParser(description="Import audiobook into Apple Books")
    p.add_argument("config", type=Path, help="book.yaml from ripper output")
    args = p.parse_args()

    with open(args.config) as f:
        meta = yaml.safe_load(f)

    if "import path" not in meta:
        sys.exit("YAML missing required key: import path")

    book_dir = Path(meta["import path"]) / meta["title"].replace(" ", "_")
    if not book_dir.exists():
        sys.exit(f"Book directory not found: {book_dir}")

    import_book(book_dir)

if __name__ == "__main__":
    main()

