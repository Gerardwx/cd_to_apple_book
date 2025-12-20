import argparse, platform, sys, yaml
from pathlib import Path
from .util import setup_logging
from . import ripper, importer

OS = platform.system()

def load_cfg(p: Path) -> dict:
    with p.open() as f: return yaml.safe_load(f)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log-level", default="INFO")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("rip")
    r.add_argument("config", type=Path)

    i = sub.add_parser("import")
    i.add_argument("path", type=Path)

    args = p.parse_args()
    setup_logging(args.log_level)

    if args.cmd == "rip":
        if OS != "Linux": sys.exit("rip must run on Linux")
        cfg = load_cfg(args.config)
        book = Path(cfg.get("rip path", cfg["title"]))
        for d in range(1, cfg["cds"] + 1):
            ripper.rip_cd(book, d)
        ripper.write_yaml(book, cfg)

    if args.cmd == "import":
        if OS != "Darwin": sys.exit("import must run on macOS")
        importer.import_book(args.path)

