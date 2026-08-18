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


def main() -> int:
    """Build both distributions, inspect required files, and return a status."""
    with tempfile.TemporaryDirectory(prefix="detection-mcp-build-") as directory:
        output = Path(directory)
        subprocess.run(  # noqa: S603
            [UV, "build", "--no-sources", "--out-dir", str(output)], cwd=ROOT, check=True
        )
        wheel = next(output.glob("*.whl"))
        source = next(output.glob("*.tar.gz"))
        with zipfile.ZipFile(wheel) as archive:
            wheel_names = set(archive.namelist())
        bundled_skills = sorted(name for name in wheel_names if name.startswith("detection_mcp/skills/"))
        if bundled_skills:
            print("Wheel must not bundle repository Agent Skills.", file=sys.stderr)
            return 1
        with tarfile.open(source, "r:gz") as archive:
            source_names = archive.getnames()
        if any("/skills/" in name and name.endswith("/SKILL.md") for name in source_names):
            print("Source distribution must not bundle repository Agent Skills.", file=sys.stderr)
            return 1
        print(f"Verified {wheel.name} and {source.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
