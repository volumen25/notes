#!/usr/bin/env python3
import shutil
import os
from pathlib import Path
import yaml

def clear_screen():
    """Clear the terminal screen (cross-platform)."""
    os.system("cls" if os.name == "nt" else "clear")

# Clear terminal at the start
clear_screen()

SOURCE_DIR = Path.home() / "Documents/codeberg/content"
TARGET_DIR = Path.home() / "Documents/notes/content"

TARGET_DIR.mkdir(parents=True, exist_ok=True)

copied = 0
skipped = 0

for file in SOURCE_DIR.rglob("*.md"):
    # Extract YAML front matter
    yaml_text = []
    with file.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            yaml_text.append(line)

    if not yaml_text:
        continue

    try:
        meta = yaml.safe_load("".join(yaml_text)) or {}
    except Exception:
        continue

    tags = meta.get("tags")
    if tags is None:
        tags = []
    elif isinstance(tags, str):
        tags = [tags]
    elif not isinstance(tags, list):
        tags = [str(tags)]

    if "volumen" in tags:
        rel_path = file.relative_to(SOURCE_DIR)
        dest_file = TARGET_DIR / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if not dest_file.exists() or file.stat().st_mtime > dest_file.stat().st_mtime:
            shutil.copy2(file, dest_file)
            copied += 1
            print(f"Copied: {rel_path}")
        else:
            skipped += 1

print(f"{copied} copied, {skipped} skipped.")