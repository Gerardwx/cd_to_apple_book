from pathlib import Path
import subprocess, yaml

def import_book(book_dir):
    if not (book_dir/"COMPLETE").exists():
        raise RuntimeError("Not complete")
    with open(book_dir/"book.yaml") as f:
        meta=yaml.safe_load(f)
    tracks=sorted(book_dir.glob("disc*/**/*.m4a"))
    concat=book_dir/"concat.txt"
    concat.write_text("\n".join(f"file '{t.resolve()}'" for t in tracks))
    m4b=book_dir/f"{meta['title']}.m4b"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c:a","copy",m4b], check=True)
    subprocess.run(["osascript","-e",f'tell application "Books" to add POSIX file "{m4b.resolve()}"'], check=True)
