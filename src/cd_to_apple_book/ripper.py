from pathlib import Path
import subprocess
import time 
import yaml

from .util import confirm

try:
    from .musicbrainz import choose_release, extract_metadata
    HAVE_MUSICBRAINZ = True
except ImportError:
    HAVE_MUSICBRAINZ = False


def load_cfg(p: Path) -> dict:
    with p.open() as f: return yaml.safe_load(f)


def fetch_musicbrainz_metadata(*, expected: dict, interactive: bool) -> dict:
    import musicbrainzngs
    musicbrainzngs.set_useragent("ripper", "1.0", "https://example.org")

    result = musicbrainzngs.search_releases(
        artist=expected.get("author"),
        release=expected.get("title"),
        limit=10,
    )

    releases = result.get("release-list", [])
    release = choose_release(releases, expected=expected, interactive=interactive)
    if not release: raise RuntimeError("No suitable MusicBrainz release found")

    full = musicbrainzngs.get_release_by_id(
        release["id"], includes=["recordings"]
    )["release"]

    return extract_metadata(full)


def write_yaml(book_dir: Path, meta: dict):
    with (book_dir / "book.yaml").open("w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)


def rip_cd(
    book_dir: Path,
    disc: int,
    *,
    dry_run: bool = False,
):
    disc_dir = book_dir / f"disc{disc}"

    if disc_dir.exists() and any(disc_dir.glob("*.m4a")):
        print(f"Disc {disc} already ripped — skipping")
        return

    if dry_run:
        print(f"[DRY-RUN] Would create {disc_dir}")
        print("[DRY-RUN] Would run abcde in disc directory")
        return

    disc_dir.mkdir(parents=True, exist_ok=True)
    confirm(f"Insert CD {disc}")

    start = time.monotonic()
    subprocess.run(["abcde", "-o", "m4a"], cwd=disc_dir, check=True)
    elapsed = time.monotonic() - start

    mins, secs = divmod(int(elapsed), 60)
    print(f"Disc {disc} ripped in {mins}m {secs}s")

def old_rip_cd(
    book_dir: Path,
    disc: int,
    *,
    dry_run: bool = False,
):
    disc_dir = book_dir / f"disc{disc}"

    if disc_dir.exists() and any(disc_dir.glob("*.m4a")):
        print(f"Disc {disc} already ripped — skipping")
        return

    if dry_run:
        print(f"[DRY-RUN] Would create {disc_dir}")
        print("[DRY-RUN] Would run abcde in disc directory")
        return

    disc_dir.mkdir(parents=True, exist_ok=True)
    confirm(f"Insert CD {disc}")
    subprocess.run(["abcde", "-o", "m4a"], cwd=disc_dir, check=True)


def main():
    import argparse, platform, sys

    if platform.system() != "Linux":
        sys.exit("rip must run on Linux")

    p = argparse.ArgumentParser(description="Rip audiobook CDs")
    p.add_argument("config", type=Path, help="YAML config file")
    p.add_argument("--start-disc", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    cfg = load_cfg(args.config)
    if "cds" not in cfg or "title" not in cfg:
        sys.exit("YAML must contain at least: title, cds")

    rip_root = Path(cfg.get("rip path", ".")).expanduser()
    book_dir = rip_root / cfg["title"].replace(" ", "_")
    book_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(book_dir, cfg)

    for disc in range(args.start_disc, cfg["cds"] + 1):
        rip_cd(book_dir, disc, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

