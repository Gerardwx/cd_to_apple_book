from pathlib import Path
import argparse, platform, sys, subprocess, time, os, yaml
from .util import confirm

def load_cfg(p: Path) -> dict:
    with p.open() as f: return yaml.safe_load(f)

def write_yaml(book_dir: Path, meta: dict):
    with (book_dir / "book.yaml").open("w") as f:
        yaml.safe_dump(meta, f, sort_keys=False)

def rip_cd(
    book_dir: Path,
    disc: int,
    *,
    relaxed: bool,
    paranoid: bool,
    dry_run: bool,
):
    disc_dir = book_dir / f"disc{disc}"

    if disc_dir.exists() and any(disc_dir.glob("*.m4a")):
        print(f"Disc {disc} already ripped — skipping")
        return

    disc_dir.mkdir(parents=True, exist_ok=True)
    confirm(f"Insert CD {disc}")

    cmd = ["abcde", "-o", "m4a"]
    if disc != 1:
        cmd.append("-N")  # non-interactive for discs > 1

    def run(env_opts: str | None):
        env = os.environ if not env_opts else os.environ | {"CDPARANOIAOPTS": env_opts}
        start = time.monotonic()
        subprocess.run(cmd, cwd=disc_dir, env=env, check=True)
        elapsed = time.monotonic() - start
        m, s = divmod(int(elapsed), 60)
        print(f"Disc {disc} ripped in {m}m {s}s")

    if dry_run:
        mode = "paranoid" if paranoid else "relaxed+fallback"
        print(f"[DRY-RUN] Would rip disc {disc} ({mode})")
        return

    if paranoid:
        run(None); return
    if relaxed:
        run("--never-skip"); return

    try:
        run("--never-skip")
    except subprocess.CalledProcessError:
        print(f"Disc {disc} failed in relaxed mode — retrying paranoid")
        run(None)

def main():
    OS = platform.system()
    if OS != "Linux": sys.exit("rip must run on Linux")
    if platform.system() != "Linux":
        sys.exit("rip must run on Linux")

    p = argparse.ArgumentParser(description="Rip audiobook CDs")
    p.add_argument("config", type=Path, help="YAML config file")
    p.add_argument("--start-disc", type=int, default=1)
    p.add_argument("--relaxed", action="store_true", help="Relaxed paranoia (fast)")
    p.add_argument("--paranoid", action="store_true", help="Full paranoia (slow)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.relaxed and args.paranoid:
        p.error("--relaxed and --paranoid are mutually exclusive")

    cfg = load_cfg(args.config)
    for k in ("title", "cds"):
        if k not in cfg:
            sys.exit(f"YAML missing required key: {k}")

    rip_root = Path(cfg.get("rip path", ".")).expanduser()
    book_dir = rip_root / cfg["title"].replace(" ", "_")
    book_dir.mkdir(parents=True, exist_ok=True)

    write_yaml(book_dir, cfg)

    for disc in range(args.start_disc, cfg["cds"] + 1):
        rip_cd(
            book_dir,
            disc,
            relaxed=args.relaxed,
            paranoid=args.paranoid,
            dry_run=args.dry_run,
        )

if __name__ == "__main__":
    main()

