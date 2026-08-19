"""Validate repository Agent Skill structure and local links."""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOTS = (ROOT / "skills", ROOT / ".agents" / "skills")
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_PATTERN = re.compile(r"\[[^]]*]\(([^)]+)\)")


def validate_skill(skill_dir: Path) -> list[str]:
    """Return structural and link errors for one canonical Agent Skill."""
    errors: list[str] = []
    entrypoint = skill_dir / "SKILL.md"
    if not entrypoint.is_file():
        return [f"{skill_dir.relative_to(ROOT)}: missing SKILL.md"]

    text = entrypoint.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        return [f"{entrypoint.relative_to(ROOT)}: invalid YAML frontmatter"]
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        return [f"{entrypoint.relative_to(ROOT)}: frontmatter must be a mapping"]

    name = metadata.get("name")
    description = metadata.get("description")
    if name != skill_dir.name:
        errors.append(f"{entrypoint.relative_to(ROOT)}: name must match its directory")
    if not isinstance(name, str) or len(name) > 64 or NAME_PATTERN.fullmatch(name) is None:
        errors.append(f"{entrypoint.relative_to(ROOT)}: invalid skill name")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        errors.append(f"{entrypoint.relative_to(ROOT)}: description must contain 1-1024 characters")

    linked_files: set[Path] = set()
    for raw_link in LINK_PATTERN.findall(parts[2]):
        if "://" in raw_link or raw_link.startswith("#"):
            continue
        target = (skill_dir / raw_link.split("#", 1)[0]).resolve()
        if not target.is_relative_to(skill_dir.resolve()):
            errors.append(f"{entrypoint.relative_to(ROOT)}: link escapes the skill directory: {raw_link}")
        elif not target.exists():
            errors.append(f"{entrypoint.relative_to(ROOT)}: broken link: {raw_link}")
        elif target.is_file():
            linked_files.add(target)

    bundled_files = {
        path.resolve()
        for folder in ("references", "scripts", "assets")
        for path in (skill_dir / folder).glob("**/*")
        if path.is_file()
    }
    for unlinked in sorted(bundled_files - linked_files):
        errors.append(f"{entrypoint.relative_to(ROOT)}: bundled file is not linked: {unlinked.relative_to(skill_dir)}")
    if (skill_dir / "README.md").exists():
        errors.append(f"{skill_dir.relative_to(ROOT)}: skill roots must not contain README.md")
    return errors


def main() -> int:
    """Validate repository Agent Skills and return a status."""
    errors: list[str] = []
    skill_dirs = sorted(
        path for skills_root in SKILL_ROOTS if skills_root.exists() for path in skills_root.iterdir() if path.is_dir()
    )
    if not skill_dirs:
        errors.append("no Agent Skill directories found")
    for skill_dir in skill_dirs:
        errors.extend(validate_skill(skill_dir))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(skill_dirs)} Agent Skills across skills/ and .agents/skills/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
