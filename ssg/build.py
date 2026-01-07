#!/usr/bin/env python3
import os
import shutil
from pathlib import Path
import yaml
import glob
import subprocess
import re
import html
import sys
import logging
import time
from datetime import datetime, timezone, timedelta, date
from email.utils import format_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

# ----------------------------
# Base directories
# ----------------------------
BASE_DIR = Path(__file__).parent.parent  # project root (notes/)
SSG_DIR = Path(__file__).parent  # ssg/
ASSETS_DIR = BASE_DIR / "assets"  # assets/
CONTENT_DIR = BASE_DIR / "content"  # content/ in project root
OUTPUT_DIR = BASE_DIR / "docs"  # output directory
FRAG_DIR = SSG_DIR / "fragments"  # temporary HTML fragments

# Ensure directories exist
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
FRAG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------
# Generate HTML and RSS
# ----------------------------
def generate():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info("Starting build process.")

    # === Configuration ===
    CONFIG = {
        "content_dir": str(CONTENT_DIR),
        "intro_md": str(CONTENT_DIR / "intro.md"),
        "colophon_md": str(CONTENT_DIR / "colophon.md"),
        "css_file": "typewriter.css",  # Relative path (in same dir as index.html)
        "bib_file": str(ASSETS_DIR / "refs.json"),
        "csl_file": str(ASSETS_DIR / "apa.csl"),
        "lua_filter": str(ASSETS_DIR / "md-to-html-links.lua"),
        "frag_dir": str(FRAG_DIR),
        "final_html": str(OUTPUT_DIR / "index.html"),
        "rss_file": str(OUTPUT_DIR / "rss.xml"),
        "favicon": "favicon.ico",  # Relative path (in same dir as index.html)
        "title": "Volūmen",
        "site_url": "https://notes.volumen.ca/",
        "rss_description": "Updates and notes from Volūmen",
        "rss_description_length": 300,
        "viewport": "width=device-width, initial-scale=1.0, user-scalable=yes",
        "generator": subprocess.run(
            ["pandoc", "--version"], capture_output=True, text=True
        ).stdout.splitlines()[0],
    }

    # === Copy .md files from source to content/ ===
    SOURCE_DIR = Path.home() / "Documents/codeberg/content"
    copied = 0
    skipped = 0

    for file in SOURCE_DIR.rglob("*.md"):
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
            dest_file = CONTENT_DIR / rel_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            if (
                not dest_file.exists()
                or file.stat().st_mtime > dest_file.stat().st_mtime
            ):
                shutil.copy2(file, dest_file)
                copied += 1
            else:
                skipped += 1

    logging.info(f"{copied} copied, {skipped} skipped from source directory.")

    # === HTML Parser to extract text from 2nd <p> tag ===
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
            self.p_count = 0
            self.in_target_p = False

        def handle_starttag(self, tag, attrs):
            if tag == "p":
                self.p_count += 1
                if self.p_count == 2:
                    self.in_target_p = True

        def handle_endtag(self, tag):
            if tag == "p":
                self.in_target_p = False

        def handle_data(self, data):
            if self.in_target_p:
                self.text.append(data.strip())

        def get_text(self, max_length):
            text = " ".join(self.text).strip()
            text = re.sub(r"\s+([.,;])", r"\1", text)
            if not text:
                return "No description available."
            if len(text) > max_length:
                text = text[: max_length - 3].rsplit(" ", 1)[0] + "..."
            return text

    # === Process intro.md ===
    intro_html = ""
    if os.path.exists(CONFIG["intro_md"]):
        temp_md = FRAG_DIR / "intro.tmp.md"
        output_html = FRAG_DIR / "intro.html"
        try:
            with (
                open(CONFIG["intro_md"], "r", encoding="utf-8") as src,
                open(temp_md, "w", encoding="utf-8") as dst,
            ):
                dst.write(src.read())

            subprocess.run(
                [
                    "pandoc",
                    str(temp_md),
                    "-t",
                    "html",
                    "-o",
                    str(output_html),
                    "--syntax-highlighting=none",
                    "--file-scope",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with open(output_html, "r", encoding="utf-8") as f:
                intro_html = f.read()
        except subprocess.CalledProcessError as e:
            logging.warning(f"Failed to process intro.md: {e.stderr}")
        finally:
            if temp_md.exists():
                temp_md.unlink()

    # === Process colophon.md ===
    colophon_html = ""
    if os.path.exists(CONFIG["colophon_md"]):
        temp_md = FRAG_DIR / "colophon.tmp.md"
        output_html = FRAG_DIR / "colophon.html"
        try:
            with (
                open(CONFIG["colophon_md"], "r", encoding="utf-8") as src,
                open(temp_md, "w", encoding="utf-8") as dst,
            ):
                dst.write(src.read())

            subprocess.run(
                [
                    "pandoc",
                    str(temp_md),
                    "-t",
                    "html",
                    "-o",
                    str(output_html),
                    "--syntax-highlighting=none",
                    "--file-scope",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with open(output_html, "r", encoding="utf-8") as f:
                colophon_html = f.read()
        except subprocess.CalledProcessError as e:
            logging.warning(f"Failed to process colophon.md: {e.stderr}")
        finally:
            if temp_md.exists():
                temp_md.unlink()

    # === Collect Markdown files ===
    md_files = [
        f
        for f in glob.glob(str(CONTENT_DIR / "*.md"))
        if not os.path.basename(f).startswith("README")
        and os.path.abspath(f) != os.path.abspath(CONFIG["intro_md"])
        and os.path.abspath(f) != os.path.abspath(CONFIG["colophon_md"])
    ]

    if not md_files:
        logging.warning("No Markdown files found in content directory.")

    anchor_counts = {}
    bar_length = 30

    # === Function to process a single Markdown file ===
    def process_file(md_file):
        stem = os.path.splitext(os.path.basename(md_file))[0]
        frag_html = FRAG_DIR / f"{stem}.html"

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logging.error(f"{md_file} is not UTF-8 encoded. Skipping.")
            return frag_html, None

        title, date_str, body = "Untitled", "", content
        date_obj = datetime.fromtimestamp(os.path.getmtime(md_file), tz=timezone.utc)

        # --- Parse YAML front matter if present ---
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                metadata, body = parts[1], parts[2]
                metadata_lines = [
                    line
                    for line in metadata.splitlines()
                    if not line.strip().startswith("subtitle:")
                ]
                metadata = yaml.safe_load("\n".join(metadata_lines)) or {}
                title = metadata.get("title", title)
                date_str = metadata.get("date", "")

                if date_str:
                    try:
                        if isinstance(date_str, date):
                            # Use noon UTC to ensure correct date display in all timezones
                            date_obj = datetime.combine(
                                date_str,
                                datetime.min.time().replace(hour=12),
                                tzinfo=timezone.utc,
                            )
                        else:
                            # Parse date and set to noon UTC
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(
                                hour=12,
                                minute=0,
                                second=0,
                                microsecond=0,
                                tzinfo=timezone.utc,
                            )
                    except Exception:
                        pass

                body = body.strip()
            except Exception:
                pass

        # --- Generate unique anchor ---
        anchor_base = re.sub(r"[^\w\-]", "", title.lower().replace(" ", "-"))
        anchor = anchor_base
        if anchor in anchor_counts:
            anchor_counts[anchor] += 1
            anchor = f"{anchor_base}-{anchor_counts[anchor]}"
        else:
            anchor_counts[anchor] = 0

        # --- Run Pandoc ---
        pandoc_input = (
            f"# {title} {{#{anchor}}}\n{date_str}\n\n{body}\n\n::: {{#refs}}\n:::\n"
        )
        try:
            result = subprocess.run(
                [
                    "pandoc",
                    "-f",
                    "markdown",
                    "-t",
                    "html",
                    "--syntax-highlighting=none",
                    "--citeproc",
                    "--file-scope",
                    f"--bibliography={CONFIG['bib_file']}",
                    f"--csl={CONFIG['csl_file']}",
                    "--lua-filter",
                    CONFIG["lua_filter"],
                ],
                input=pandoc_input,
                text=True,
                capture_output=True,
                check=True,
            )

            with open(frag_html, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            parser = TextExtractor()
            parser.feed(result.stdout)
            description = parser.get_text(CONFIG["rss_description_length"])
        except subprocess.CalledProcessError as e:
            logging.warning(f"Pandoc failed for {md_file}: {e.stderr}")
            description = "No description available."

        return frag_html, (title, anchor, date_obj, date_str, description)

    # === Process all Markdown files in parallel ===
    fragment_meta_pairs = []
    max_filename_length = max((len(os.path.basename(f)) for f in md_files), default=0)
    max_line_length = (
        bar_length + len("[] 100.0% (XX/XX) processed ") + max_filename_length
    )

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        futures = {executor.submit(process_file, f): f for f in md_files}
        for completed, future in enumerate(as_completed(futures), start=1):
            frag, meta = future.result()
            if meta:
                fragment_meta_pairs.append((frag, meta))

            percent = completed / len(md_files) if md_files else 1
            filled = int(bar_length * percent)
            bar = "#" * filled + "-" * (bar_length - filled)
            sys.stdout.write(
                f"\r[{bar}] {percent:>5.1%} ({completed}/{len(md_files)}) processed"
            )
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * max_line_length + "\r")
    sys.stdout.flush()

    # === Sort fragments by newest first ===
    fragment_meta_pairs.sort(key=lambda x: x[1][2], reverse=True)

    # === Assemble index.html ===
    with open(CONFIG["final_html"], "w", encoding="utf-8") as index:
        index.write(
            f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="generator" content="{CONFIG['generator']}">
    <meta name="viewport" content="{CONFIG['viewport']}">
    <title>{CONFIG['title']}</title>
    <link rel="icon" type="image/x-icon" href="{CONFIG['favicon']}">
    <link rel="stylesheet" href="{CONFIG['css_file']}">
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="rss.xml">
</head>
<body>
    <h1>{CONFIG['title']}</h1>
{intro_html + '\n<hr>\n' if intro_html else ''}
"""
        )

        for frag_path, _ in fragment_meta_pairs:
            if os.path.exists(frag_path):
                with open(frag_path, "r", encoding="utf-8") as frag:
                    index.write(frag.read() + "\n<hr>\n")
            else:
                logging.warning(f"Fragment {frag_path} not found. Skipping.")

        # === Add colophon before ToC ===
        if colophon_html:
            index.write(colophon_html + "\n<hr>\n")

        toc_entries = [(m[0], m[1]) for _, m in fragment_meta_pairs]
        index.write("<h1>Index</h1>\n<ul>\n")
        for title, anchor in toc_entries:
            index.write(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>\n')
        index.write("</ul>\n</body>\n</html>\n")

    logging.info(f"Page generated → {CONFIG['final_html']}")

    # === Generate RSS feed ===
    pub_dates_used = set()
    with open(CONFIG["rss_file"], "w", encoding="utf-8") as rss:
        rss.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
        rss.write(
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
        )
        rss.write(f'<title>{CONFIG["title"]}</title>\n')
        rss.write(f'<link>{CONFIG["site_url"]}</link>\n')
        rss.write(f'<description>{CONFIG["rss_description"]}</description>\n')
        rss.write(
            f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>\n"
        )
        rss.write(
            f'<atom:link href="{CONFIG["site_url"]}rss.xml" rel="self" type="application/rss+xml" />\n'
        )

        for _, meta in fragment_meta_pairs[:20]:
            title, anchor, date_obj, date_str, description = meta
            pub_date = date_obj
            while pub_date in pub_dates_used:
                pub_date += timedelta(seconds=1)
            pub_dates_used.add(pub_date)

            rss.write("<item>\n")
            rss.write(f"<title>{html.escape(title)}</title>\n")
            rss.write(f"<link>{CONFIG['site_url']}index.html#{anchor}</link>\n")
            rss.write(f"<guid>{CONFIG['site_url']}index.html#{anchor}</guid>\n")
            rss.write(f"<description>{html.escape(description)}</description>\n")
            rss.write(f"<pubDate>{format_datetime(pub_date)}</pubDate>\n")
            rss.write("</item>\n")

        rss.write("</channel>\n</rss>\n")

    logging.info(f"RSS feed generated → {CONFIG['rss_file']}")

    # === Copy assets to output directory ===
    assets_to_copy = [
        (ASSETS_DIR / "typewriter.css", OUTPUT_DIR / "typewriter.css"),
        (ASSETS_DIR / "favicon.ico", OUTPUT_DIR / "favicon.ico"),
    ]

    for src, dst in assets_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            logging.info(f"Copied {src.name} → {dst}")
        else:
            logging.warning(f"Asset not found: {src}")


# ----------------------------
# Entry point
# ----------------------------
def main() -> None:
    start = time.time()
    generate()
    logging.info(f"Total process completed in {time.time() - start:.2f}s")


if __name__ == "__main__":
    main()
