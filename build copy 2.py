#!/usr/bin/env python3
import os
import glob
import subprocess
import yaml
import re
import html
import sys
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

# === Configuration ===
CONFIG = {
    "content_dir": "content",
    "intro_md": os.path.join("content", "intro.md"),
    "css_file": "typewriter.css",
    "bib_file": "refs.json",
    "csl_file": "apa.csl",
    "frag_dir": "fragments",
    "final_html": "index.html",
    "title": "Volūmen",
    "generator": "pandoc 3.7.0.2",
    "viewport": "width=device-width, initial-scale=1.0, user-scalable=yes",
    "site_url": "https://notes.volumen.ca/",
    "rss_description": "Updates and notes from Volūmen",  # New field
}

# [Previous sections unchanged: File/Directory Validation, Process intro.md]

# === Process Markdown files ===
md_files = sorted(
    [
        f for f in glob.glob(os.path.join(CONFIG["content_dir"], "*.md"))
        if not os.path.basename(f).startswith("README")
        and os.path.abspath(f) != os.path.abspath(CONFIG["intro_md"])
    ],
    reverse=True
)

fragment_paths = []
toc_entries = []
metadata_list = []  # store (title, anchor, date_obj, date_str, description)

total_files = len(md_files)
bar_length = 30
now = datetime.now(timezone.utc)

for i, md_file in enumerate(md_files, start=1):
    # Progress bar
    percent = i / total_files
    filled = int(bar_length * percent)
    bar = "#" * filled + "-" * (bar_length - filled)
    sys.stdout.write(f"\r[{bar}] {percent:>5.1%} ({i}/{total_files}) Processing {os.path.basename(md_file)}")
    sys.stdout.flush()

    with open(md_file, "r", encoding="utf-8") as infile:
        content = infile.read()
    title, date_str, body = "Untitled", "", content.strip()
    date_obj = None
    description = ""  # Initialize description
    if content.startswith("---"):
        try:
            metadata, body = content.split("---", 2)[1:3]
            metadata = yaml.safe_load(metadata)
            title = metadata.get("title", title)
            date_str = metadata.get("date", "")
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    date_obj = None
            body = body.strip()
            # Extract first 200 characters of body for RSS description
            description = body[:200].replace("\n", " ").strip() + "..." if body else ""
        except Exception:
            pass

    if not date_obj:  # Use file modification time as fallback
        date_obj = datetime.fromtimestamp(os.path.getmtime(md_file), tz=timezone.utc)

    anchor = re.sub(r"[^\w\-]", "", title.lower().replace(" ", "-"))
    toc_entries.append((title, anchor))
    metadata_list.append((title, anchor, date_obj, date_str, description))

    stem = os.path.splitext(os.path.basename(md_file))[0]
    temp_md = os.path.join(CONFIG["frag_dir"], f"{stem}.tmp.md")
    frag_html = os.path.join(CONFIG["frag_dir"], f"{stem}.html")
    fragment_paths.append(frag_html)

    with open(temp_md, "w", encoding="utf-8") as tmp:
        tmp.write(f"# {title} {{#{anchor}}}\n{date_str}\n\n{body}\n\n::: {{#refs}}\n:::\n")
    try:
        subprocess.run(
            [
                "pandoc", temp_md, "-o", frag_html,
                "--css", CONFIG["css_file"], "--no-highlight", "--citeproc",
                "--file-scope",
                f"--bibliography={CONFIG['bib_file']}",
                f"--csl={CONFIG['csl_file']}"
            ],
            check=True, capture_output=True, text=True
        )
        os.remove(temp_md)
    except subprocess.CalledProcessError:
        continue

# Clear progress bar line
print()

# [HTML Generation section unchanged]

# === Generate RSS feed (10 most recent, newest first) ===
rss_file = "rss.xml"
last_build = format_datetime(now)

with open(rss_file, "w", encoding="utf-8") as rss:
    rss.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    rss.write('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n')
    rss.write(f'<title>{CONFIG["title"]}</title>\n')
    rss.write(f'<link>{CONFIG["site_url"]}</link>\n')
    rss.write(f'<description>{CONFIG["rss_description"]}</description>\n')
    rss.write(f"<lastBuildDate>{last_build}</lastBuildDate>\n")
    # Add Atom self-link
    rss.write(f'<atom:link href="{CONFIG["site_url"]}rss.xml" rel="self" type="application/rss+xml" />\n')

    # Sort metadata by date_obj (newest first)
    sorted_metadata = sorted(
        metadata_list,
        key=lambda x: x[2] if x[2] else now,
        reverse=True
    )

    # Ensure unique pubDate for each item
    used_dates = set()
    for title, anchor, date_obj, date_str, description in sorted_metadata[:10]:
        pub_date = date_obj
        # Increment by 1 second if duplicate timestamp
        while pub_date in used_dates:
            pub_date += timedelta(seconds=1)
        used_dates.add(pub_date)

        pub_date_str = format_datetime(pub_date)
        rss.write("<item>\n")
        rss.write(f"<title>{html.escape(title)}</title>\n")
        rss.write(f"<link>{CONFIG['site_url']}index.html#{anchor}</link>\n")
        rss.write(f"<guid>{CONFIG['site_url']}index.html#{anchor}</guid>\n")
        rss.write(f"<description>{html.escape(description)}</description>\n")
        rss.write(f"<pubDate>{pub_date_str}</pubDate>\n")
        rss.write("</item>\n")

    rss.write("</channel>\n</rss>\n")

print(f"RSS feed generated → {rss_file}")