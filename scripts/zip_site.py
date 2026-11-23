"""Zip a static site with clean, forward-slash entry names (no ./ prefix) for Amplify upload."""
import sys
import zipfile
from pathlib import Path

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
if target.exists():
    target.unlink()
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(source.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(source).as_posix())
print(f"zipped {sum(1 for _ in zipfile.ZipFile(target).namelist())} files -> {target}")
