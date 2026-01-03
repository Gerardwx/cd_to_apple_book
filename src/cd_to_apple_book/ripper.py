from pathlib import Path
import argparse, platform, sys, subprocess, time, yaml
from .util import confirm

def load_cfg(p: Path) -> dict:
    with p.open() as f: return yaml.safe_load(f)

def write_yaml(book_dir: Path, meta: dict):
    with (book_dir / "book.yaml").open("w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)

def rip_cd(book_dir: Path, disc: int, *, paranoid: bool, dry_run: bool):
    disc_dir = book_dir / f"disc{disc}"
    if disc_dir.exists() and any(disc_dir.glob("*.m4a")):
        print(f"Disc {disc} already ripped — skipping")
        return
    
    disc_dir.mkdir(parents=True, exist_ok=True)
    confirm(f"Insert CD {disc}")
    
    # abcde defaults + explicit behavior
    cmd = ["abcde", "-o", "m4a"]
    if disc != 1:
        cmd.append("-N")  # non-interactive after disc 1
    
    if paranoid:
        # safest / slowest
        cmd.append("-p")
    else:
        # relaxed / faster: limit retries and paranoia overhead
        cmd += ["-j", "2"]
    
    if dry_run:
        mode = "paranoid" if paranoid else "relaxed"
        print(f"[DRY-RUN] Would run: {' '.join(cmd)} (disc {disc}, {mode})")
        return
    
    start = time.monotonic()
    
    # Try with MusicBrainz first
    try:
        subprocess.run(cmd, cwd=disc_dir, check=True)
    except subprocess.CalledProcessError as e:
        # Check if it's a MusicBrainz error (exit status 104 or contains musicbrainz error)
        print(f"⚠️  MusicBrainz lookup failed (exit {e.returncode})")
        print("Retrying without MusicBrainz metadata...")
        
        # Retry with -n flag to skip MusicBrainz
        cmd_no_mb = cmd + ["-n"]
        try:
            subprocess.run(cmd_no_mb, cwd=disc_dir, check=True)
            print("✓ Ripped successfully without MusicBrainz metadata")
        except subprocess.CalledProcessError as e2:
            print(f"✗ Rip failed even without MusicBrainz: {e2}")
            raise
    
    elapsed = time.monotonic() - start
    m, s = divmod(int(elapsed), 60)
    print(f"Disc {disc} ripped in {m}m {s}s")

def main():
    if platform.system() != "Linux":
        sys.exit("rip must run on Linux")
    
    p = argparse.ArgumentParser(description="Rip audiobook CDs")
    p.add_argument("config", type=Path, help="YAML config file")
    p.add_argument("--start-disc", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--paranoid", action="store_true", help="Full paranoia (slow)")
    mode.add_argument("--relaxed", action="store_true", help="Relaxed mode (default)")
    args = p.parse_args()
    
    # Default behavior
    paranoid = args.paranoid
    
    cfg = load_cfg(args.config)
    for k in ("title", "cds"):
        if k not in cfg:
            sys.exit(f"YAML missing required key: {k}")
    
    rip_root = Path(cfg.get("rip path", ".")).expanduser()
    book_dir = rip_root / cfg["title"].replace(" ", "_")
    book_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(book_dir, cfg)
    
    for disc in range(args.start_disc, cfg["cds"] + 1):
        rip_cd(book_dir, disc, paranoid=paranoid, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
