from pathlib import Path
import argparse
import fcntl
import platform
import sys
import subprocess
import time
import yaml
import os
from .util import confirm

# Linux ioctl constants for CD drive status
CDROM_DRIVE_STATUS = 0x5326
CDS_DISC_OK = 4

def load_cfg(p: Path) -> dict:
    with p.open() as f: 
        return yaml.safe_load(f)

def write_yaml(book_dir: Path, meta: dict):
    with (book_dir / "book.yaml").open("w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)

def make_ffmpeg_opts(audio: dict) -> str:
    """Generate FFmpeg encoder options from audio settings."""
    opts = ["-c:a aac"]

    if "bitrate" in audio:
        opts.append(f"-b:a {audio['bitrate']}")

    if "channels" in audio:
        ch = 1 if audio["channels"] == "mono" else 2
        opts.append(f"-ac {ch}")

    return " ".join(opts)

def wait_for_disc(disc: int, device: str = "/dev/cdrom", poll_interval: int = 5):
    """Poll the CD drive until a disc is detected."""
    print(f"Insert disc {disc} into {device} — waiting…", flush=True)
    while True:
        try:
            with open(device, "rb") as fd:
                status = fcntl.ioctl(fd, CDROM_DRIVE_STATUS)
            if status == CDS_DISC_OK:
                print(f"Disc {disc} detected.", flush=True)
                return
        except OSError:
            pass
        time.sleep(poll_interval)


def rip_cd(book_dir: Path, disc: int, *, paranoid: bool, dry_run: bool, audio: dict | None = None, poll: bool = False, device: str = "/dev/cdrom"):
    disc_dir = book_dir / f"disc{disc}"
    if disc_dir.exists() and any(disc_dir.glob("*.m4a")):
        print(f"Disc {disc} already ripped — skipping")
        return

    disc_dir.mkdir(parents=True, exist_ok=True)
    if poll:
        wait_for_disc(disc, device)
    else:
        confirm(f"Insert CD {disc}")

    # abcde defaults + explicit behavior
    cmd = ["abcde", "-o", "m4a", "-d", device]
    if disc != 1:
        cmd.append("-N")  # non-interactive after disc 1

    if paranoid:
        # safest / slowest
        cmd.append("-p")
    else:
        # relaxed / faster: limit retries and paranoia overhead
        cmd += ["-j", "2"]

    # Prepare environment with audio settings if provided
    env = os.environ.copy()
    if audio:
        env["FFMPEGENCOPTS"] = make_ffmpeg_opts(audio)

    if dry_run:
        mode = "paranoid" if paranoid else "relaxed"
        audio_info = f" with FFMPEGENCOPTS={env['FFMPEGENCOPTS']}" if audio else ""
        print(f"[DRY-RUN] Would run: {' '.join(cmd)} (disc {disc}, {mode}){audio_info}")
        return

    start = time.monotonic()

    # Try with MusicBrainz first
    try:
        subprocess.run(cmd, cwd=disc_dir, env=env, check=True)
    except subprocess.CalledProcessError as e:
        # Check if it's a MusicBrainz error (exit status 104 or contains musicbrainz error)
        print(f"⚠️  MusicBrainz lookup failed (exit {e.returncode})")
        print("Retrying without MusicBrainz metadata...")

        worked = False
        while not worked:
            # Retry with -n flag to skip MusicBrainz
            cmd_no_mb = cmd + ["-n"]
            try:
                subprocess.run(cmd_no_mb, cwd=disc_dir, env=env, check=True)
                print("✓ Ripped successfully without MusicBrainz metadata")
                worked = True
            except KeyboardInterrupt:
                print("Ctrl-C")
                sys.exit(1)
            except subprocess.CalledProcessError as e2:
                sleep = 5
                print(f"✗ Rip failed even without MusicBrainz: {e2}, sleeping {sleep}")
                time.sleep(sleep)

    subprocess.run('/usr/bin/eject')
    elapsed = time.monotonic() - start
    m, s = divmod(int(elapsed), 60)
    print(f"Disc {disc} ripped in {m}m {s}s")

def main():
    if platform.system() != "Linux":
        sys.exit("rip must run on Linux")
    
    p = argparse.ArgumentParser(description="Rip audiobook CDs")
    p.add_argument("config", type=Path, help="YAML config file")
    p.add_argument("--start-disc", type=int, default=1, help="disc to start or resume with")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-poll", action="store_true", help="Wait for ENTER instead of polling the drive for disc insertion")
    p.add_argument("--device", default="/dev/cdrom", help="CD drive device (default: /dev/cdrom)")
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

    audio = cfg.get("audio")

    for disc in range(args.start_disc, cfg["cds"] + 1):
        rip_cd(book_dir, disc, paranoid=paranoid, dry_run=args.dry_run, audio=audio, poll=not args.no_poll, device=args.device)

if __name__ == "__main__":
    main()
