from pathlib import Path
import subprocess
import yaml

from .util import confirm

try:
    from .musicbrainz import choose_release, extract_metadata
    HAVE_MUSICBRAINZ = True
except ImportError:
    HAVE_MUSICBRAINZ = False


def fetch_musicbrainz_metadata(*, expected: dict, interactive: bool) -> dict:
    import musicbrainzngs

    musicbrainzngs.set_useragent(
        "ripper",
        "1.0",
        "https://example.org",
    )

    result = musicbrainzngs.search_releases(
        artist=expected.get("author"),
        release=expected.get("title"),
        limit=10,
    )

    releases = result.get("release-list", [])
    release = choose_release(
        releases,
        expected=expected,
        interactive=interactive,
    )

    if not release:
        raise RuntimeError("No suitable MusicBrainz release found")

    full = musicbrainzngs.get_release_by_id(
        release["id"],
        includes=["recordings"],
    )["release"]

    return extract_metadata(full)


def write_yaml(book_dir: Path, meta: dict):
    with open(book_dir / "book.yaml", "w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)
    (book_dir / "COMPLETE").touch()


def rip_cd(
    book_dir: Path,
    disc: int,
    *,
    use_musicbrainz: bool = False,
    expected: dict | None = None,
    interactive: bool = False,
    dry_run: bool = False,
):
    disc_dir = book_dir / f"disc{disc}"

    if dry_run:
        print(f"[DRY-RUN] Would create {disc_dir}")
    else:
        disc_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print("[DRY-RUN] Would rip CD with abcde")
    else:
        confirm(f"Insert CD {disc}")
        subprocess.run(["abcde", "-o", "m4a"], check=True)

    if dry_run:
        print("[DRY-RUN] Would move ripped .m4a files")
    else:
        for f in Path(".").glob("*.m4a"):
            f.rename(disc_dir / f.name)

    if use_musicbrainz:
        if not HAVE_MUSICBRAINZ:
            raise RuntimeError("MusicBrainz support requested but not available")

        if not expected:
            raise ValueError("expected metadata required with --musicbrainz")

        meta = fetch_musicbrainz_metadata(
            expected=expected,
            interactive=interactive,
        )

        if dry_run:
            print("[DRY-RUN] Would write book.yaml:")
            print(yaml.safe_dump(meta, sort_keys=False))
        else:
            write_yaml(book_dir, meta)


def main():
    import argparse

    p = argparse.ArgumentParser(
        description="Rip audio CDs into a structured audiobook directory",
    )

    p.add_argument("book_dir", type=Path, help="Target book directory")
    p.add_argument("--disc", type=int, required=True, help="Disc number")

    p.add_argument("--musicbrainz", action="store_true", help="Use MusicBrainz metadata")
    p.add_argument("--interactive", action="store_true", help="Interactively choose release")
    p.add_argument("--dry-run", action="store_true", help="Show actions without executing")

    p.add_argument("--title", help="Expected title (required with --musicbrainz)")
    p.add_argument("--author", help="Expected author (required with --musicbrainz)")

    args = p.parse_args()

    expected = None
    if args.musicbrainz:
        if not args.title or not args.author:
            p.error("--musicbrainz requires --title and --author")
        expected = {
            "title": args.title,
            "author": args.author,
        }

    rip_cd(
        book_dir=args.book_dir,
        disc=args.disc,
        use_musicbrainz=args.musicbrainz,
        interactive=args.interactive,
        expected=expected,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
