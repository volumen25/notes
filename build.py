#!/usr/bin/env python3
import os
import glob
import subprocess
import yaml
import re
import html
import sys
from datetime import datetime, timezone
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
    "site_url": "https://example.com/",  # <-- change to your site URL
}

# === Verify required files/directories ===
for file in [CONFIG["css_file"], CONFIG["bib_file"], CONFIG["csl_file"]]:
    if not os.path.exists(file):
        print(f"Error: {file} not found.")
        exit(1)
if not os.path.isdir(CONFIG["content_dir"]):
    print(f"Error: '{CONFIG['content_dir']}' directory not found.")
    exit(1)
os.makedirs(CONFIG["frag_dir"], exist_ok=True)

# === Process intro.md ===
intro_html = ""
if os.path.exists(CONFIG["intro_md"]):
    temp_md = os.path.join(CONFIG["frag_dir"], "intro.tmp.md")
    output_html = os.path.join(CONFIG["frag_dir"], "intro.html")
    with open(CONFIG["intro_md"], "r", encoding="utf-8") as src, open(temp_md, "w", encoding="utf-8") as dst:
        dst.write(src.read())
    try:
        subprocess.run(
            ["pandoc", temp_md, "-o", output_html, "--css", CONFIG["css_file"], "--no-highlight", "--file-scope"],
            check=True, capture_output=True, text=True
        )
        with open(output_html, "r", encoding="utf-8") as f:
            intro_html = f.read()
        os.remove(temp_md)
    except subprocess.CalledProcessError:
        pass

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
metadata_list = []  # store (title, anchor, date) for RSS

total_files = len(md_files)
bar_length = 30

for i, md_file in enumerate(md_files, start=1):
    # Progress bar
    percent = i / total_files
    filled = int(bar_length * percent)
    bar = "#" * filled + "-" * (bar_length - filled)
    sys.stdout.write(f"\r[{bar}] {percent:>5.1%} ({i}/{total_files}) Processing {os.path.basename(md_file)}")
    sys.stdout.flush()

    with open(md_file, "r", encoding="utf-8") as infile:
        content = infile.read()
    title, date, body = "Untitled", "", content.strip()
    if content.startswith("---"):
        try:
            metadata, body = content.split("---", 2)[1:3]
            metadata = yaml.safe_load(metadata)
            title = metadata.get("title", title)
            date = metadata.get("date", "")
            body = body.strip()
        except Exception:
            pass

    anchor = re.sub(r"[^\w\-]", "", title.lower().replace(" ", "-"))
    toc_entries.append((title, anchor))
    metadata_list.append((title, anchor, date))

    stem = os.path.splitext(os.path.basename(md_file))[0]
    temp_md = os.path.join(CONFIG["frag_dir"], f"{stem}.tmp.md")
    frag_html = os.path.join(CONFIG["frag_dir"], f"{stem}.html")
    fragment_paths.append(frag_html)

    with open(temp_md, "w", encoding="utf-8") as tmp:
        tmp.write(f"# {title} {{#{anchor}}}\n{date}\n\n{body}\n\n::: {{#refs}}\n:::\n")
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

# === Assemble index.html ===
with open(CONFIG["final_html"], "w", encoding="utf-8") as index:
    index.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="generator" content="{CONFIG['generator']}">
    <meta name="viewport" content="{CONFIG['viewport']}">
    <title>{CONFIG['title']}</title>
    <link rel="icon" type="image/x-icon" href="favicon.ico">
    <link rel="stylesheet" href="{CONFIG['css_file']}">
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="rss.xml">
</head>
<body>
    <h1>{CONFIG['title']}</h1>
    {intro_html + '\n<hr>\n' if intro_html else ''}
""")
    for frag_path in fragment_paths:
        if os.path.exists(frag_path):
            with open(frag_path, "r", encoding="utf-8") as frag:
                index.write(frag.read() + "\n<hr>\n")
    index.write("<h1>Index</h1>\n<ul>\n")
    for title, anchor in toc_entries:
        index.write(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>\n')
    index.write("</ul>\n</body>\n</html>\n")

print(f"Page generated → {CONFIG['final_html']}")

# === Generate RSS feed (10 most recent) ===
rss_file = "rss.xml"
now = datetime.now(timezone.utc)  # timezone-aware UTC datetime
last_build = format_datetime(now)

with open(rss_file, "w", encoding="utf-8") as rss:
    rss.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    rss.write('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n')
    rss.write(f'<title>{CONFIG["title"]}</title>\n')
    rss.write(f'<link>{CONFIG["site_url"]}</link>\n')
    rss.write("<description>Updates from my site</description>\n")
    rss.write(f"<lastBuildDate>{last_build}</lastBuildDate>\n")
    # Add Atom self-link
    rss.write(f'<atom:link href="{CONFIG["site_url"]}rss.xml" rel="self" type="application/rss+xml" />\n')

    # Take 10 most recent posts
    for title, anchor, date_str in metadata_list[:10]:
        try:
            pub_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = now
        pub_date_str = format_datetime(pub_date)
        rss.write("<item>\n")
        rss.write(f"<title>{html.escape(title)}</title>\n")
        rss.write(f"<link>{CONFIG['site_url']}index.html#{anchor}</link>\n")
        rss.write(f"<guid>{CONFIG['site_url']}index.html#{anchor}</guid>\n")
        rss.write(f"<pubDate>{pub_date_str}</pubDate>\n")
        rss.write("</item>\n")

    rss.write("</channel>\n</rss>\n")

print(f"RSS feed generated → {rss_file}")
