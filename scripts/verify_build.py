"""Build distributions and verify their required contents."""

import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
UV = which("uv") or "uv"
REQUIRED_WHEEL_SUFFIXES = {
    "detection_mcp/skills/detection-mcp-setup/SKILL.md",
    "detection_mcp/skills/object-detection-annotation/SKILL.md",
}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="detection-mcp-build-") as directory:
        output = Path(directory)
        subprocess.run(  # noqa: S603
            [UV, "build", "--no-sources", "--out-dir", str(output)], cwd=ROOT, check=True
        )
        wheel = next(output.glob("*.whl"))
        source = next(output.glob("*.tar.gz"))
        with zipfile.ZipFile(wheel) as archive:
            wheel_names = set(archive.namelist())
        missing = sorted(REQUIRED_WHEEL_SUFFIXES - wheel_names)
        if missing:
            print(f"Wheel is missing required files: {', '.join(missing)}", file=sys.stderr)
            return 1
        with tarfile.open(source, "r:gz") as archive:
            source_names = archive.getnames()
        for suffix in ("skills/detection-mcp-setup/SKILL.md", "skills/object-detection-annotation/SKILL.md"):
            if not any(name.endswith(suffix) for name in source_names):
                print(f"Source distribution is missing {suffix}", file=sys.stderr)
                return 1
        print(f"Verified {wheel.name} and {source.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
