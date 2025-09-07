import os
import glob
import subprocess
import yaml
import re
import html
import sys
import logging
from datetime import datetime, timezone, timedelta, date
from email.utils import format_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Configure logging ===
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logging.info("Starting script execution.")

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
    "generator": "Pandoc",
    "viewport": "width=device-width, initial-scale=1.0, user-scalable=yes",
    "site_url": "https://notes.volumen.ca/",
    "rss_description": "Updates and notes from Volūmen",
    "favicon": "favicon.ico",
}

# === Verify Pandoc installation ===
try:
    result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True)
    CONFIG["generator"] = result.stdout.split('\n')[0]
except (subprocess.CalledProcessError, FileNotFoundError):
    logging.error("Pandoc is not installed or not found in PATH.")
    sys.exit(1)

# === Verify files/directories ===
for file in [CONFIG["bib_file"], CONFIG["csl_file"]]:
    if not os.path.exists(file):
        logging.error(f"Required file {file} not found.")
        sys.exit(1)
for file in [CONFIG["css_file"], CONFIG["favicon"]]:
    if not os.path.exists(file):
        logging.warning(f"Optional file {file} not found. Proceeding without it.")
if not os.path.isdir(CONFIG["content_dir"]):
    logging.error(f"'{CONFIG['content_dir']}' directory not found.")
    sys.exit(1)
os.makedirs(CONFIG["frag_dir"], exist_ok=True)

# === Helper functions ===
def get_plain_text(body):
    if not body.strip():
        return ""
    try:
        result = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "plain"],
            input=body,
            text=True, capture_output=True, encoding="utf-8", check=True
        )
        return result.stdout.strip().replace("\n", " ")
    except subprocess.CalledProcessError:
        return body[:300].replace("\n", " ")

# === Process intro.md ===
intro_html = ""
if os.path.exists(CONFIG["intro_md"]):
    temp_md = os.path.join(CONFIG["frag_dir"], "intro.tmp.md")
    output_html = os.path.join(CONFIG["frag_dir"], "intro.html")
    try:
        with open(CONFIG["intro_md"], "r", encoding="utf-8") as src, open(temp_md, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        subprocess.run(
            ["pandoc", temp_md, "-o", output_html, "--css", CONFIG["css_file"], "--no-highlight", "--file-scope"],
            check=True, capture_output=True, text=True
        )
        with open(output_html, "r", encoding="utf-8") as f:
            intro_html = f.read()
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to process intro.md: {e.stderr}")
    finally:
        if os.path.exists(temp_md):
            os.remove(temp_md)

# === Collect Markdown files ===
md_files = [
    f for f in glob.glob(os.path.join(CONFIG["content_dir"], "*.md"))
    if not os.path.basename(f).startswith("README") and os.path.abspath(f) != os.path.abspath(CONFIG["intro_md"])
]
if not md_files:
    logging.warning("No Markdown files found in content directory.")

anchor_counts = {}
bar_length = 30
now = datetime.now(timezone.utc)
max_filename_length = max(len(os.path.basename(f)) for f in md_files) if md_files else 0
max_line_length = bar_length + len("[] 100.0% (XX/XX) processed ") + max_filename_length

# === Function to process a single Markdown file ===
def process_file(md_file):
    stem = os.path.splitext(os.path.basename(md_file))[0]
    frag_html = os.path.join(CONFIG["frag_dir"], f"{stem}.html")

    try:
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        logging.error(f"{md_file} is not UTF-8 encoded. Skipping.")
        return frag_html, None

    title, date_str, body = "Untitled", "", content
    date_obj = datetime.fromtimestamp(os.path.getmtime(md_file), tz=timezone.utc)
    description = get_plain_text(body)[:300] + "..." if body else ""

    if content.startswith("---"):
        try:
            metadata, body = content.split("---", 2)[1:3]
            metadata_lines = metadata.splitlines()
            metadata = "\n".join(line for line in metadata_lines if not line.strip().startswith("subtitle:"))
            metadata = yaml.safe_load(metadata) or {}
            title = metadata.get("title", title)
            date_str = metadata.get("date", "")
            if date_str:
                try:
                    if isinstance(date_str, date):
                        date_obj = datetime.combine(date_str, datetime.min.time(), tzinfo=timezone.utc)
                    else:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pass
            body = body.strip()
            description = get_plain_text(body)[:300] + "..." if body else description
        except Exception:
            pass  # keep defaults

    anchor_base = re.sub(r"[^\w\-]", "", title.lower().replace(" ", "-"))
    anchor = anchor_base
    if anchor in anchor_counts:
        anchor_counts[anchor] += 1
        anchor = f"{anchor_base}-{anchor_counts[anchor]}"
    else:
        anchor_counts[anchor] = 0

    pandoc_input = f"# {title} {{#{anchor}}}\n{date_str}\n\n{body}\n\n::: {{#refs}}\n:::\n"
    try:
        result = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "html",
             "--css", CONFIG["css_file"], "--no-highlight", "--citeproc",
             "--file-scope",
             f"--bibliography={CONFIG['bib_file']}",
             f"--csl={CONFIG['csl_file']}"],
            input=pandoc_input, text=True, capture_output=True, encoding="utf-8", check=True
        )
        with open(frag_html, "w", encoding="utf-8") as f:
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.warning(f"Pandoc failed for {md_file}: {e.stderr}")

    return frag_html, (title, anchor, date_obj, date_str, description)

# === Process all Markdown files in parallel ===
fragment_meta_pairs = []
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_file, f): f for f in md_files}
    for completed, future in enumerate(as_completed(futures), start=1):
        frag, meta = future.result()
        if meta:
            fragment_meta_pairs.append((frag, meta))
        percent = completed / len(md_files)
        filled = int(bar_length * percent)
        bar = "#" * filled + "-" * (bar_length - filled)
        sys.stdout.write(f"\r[{bar}] {percent:>5.1%} ({completed}/{len(md_files)}) processed")
        sys.stdout.flush()

sys.stdout.write("\r" + " " * max_line_length + "\r")
sys.stdout.flush()

# === Sort fragments by newest first ===
fragment_meta_pairs.sort(key=lambda x: x[1][2], reverse=True)

# === Assemble index.html ===
with open(CONFIG["final_html"], "w", encoding="utf-8") as index:
    favicon_tag = f'<link rel="icon" type="image/x-icon" href="{CONFIG["favicon"]}">' if os.path.exists(CONFIG["favicon"]) else ""
    index.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="generator" content="{CONFIG['generator']}">
    <meta name="viewport" content="{CONFIG['viewport']}">
    <title>{CONFIG['title']}</title>
    {favicon_tag}
    <link rel="stylesheet" href="{CONFIG['css_file']}">
    <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="rss.xml">
</head>
<body>
    <h1>{CONFIG['title']}</h1>
    {intro_html + '\n<hr>\n' if intro_html else ''}
""")
    for frag_path, _ in fragment_meta_pairs:
        if os.path.exists(frag_path):
            with open(frag_path, "r", encoding="utf-8") as frag:
                index.write(frag.read() + "\n<hr>\n")
        else:
            logging.warning(f"Fragment {frag_path} not found. Skipping.")

    toc_entries = [(m[0], m[1]) for _, m in fragment_meta_pairs]
    index.write("<h1>Index</h1>\n<ul>\n")
    for title, anchor in toc_entries:
        index.write(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>\n')
    index.write("</ul>\n</body>\n</html>\n")

logging.info(f"Page generated → {CONFIG['final_html']}")

# === Generate RSS feed ===
rss_file = "rss.xml"
last_build = format_datetime(now)

with open(rss_file, "w", encoding="utf-8") as rss:
    rss.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    rss.write('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n')
    rss.write(f'<title>{CONFIG["title"]}</title>\n')
    rss.write(f'<link>{CONFIG["site_url"]}</link>\n')
    rss.write(f'<description>{CONFIG["rss_description"]}</description>\n')
    rss.write(f"<lastBuildDate>{last_build}</lastBuildDate>\n")
    rss.write(f'<atom:link href="{CONFIG["site_url"]}rss.xml" rel="self" type="application/rss+xml" />\n')

    for _, meta in fragment_meta_pairs[:20]:
        title, anchor, date_obj, date_str, description = meta
        pub_date = date_obj
        pub_dates_used = set()
        while pub_date in pub_dates_used:
            pub_date += timedelta(seconds=1)
        pub_dates_used.add(pub_date)
        pub_date_str = format_datetime(pub_date)
        rss.write("<item>\n")
        rss.write(f"<title>{html.escape(title)}</title>\n")
        rss.write(f"<link>{CONFIG['site_url']}index.html#{anchor}</link>\n")
        rss.write(f"<guid>{CONFIG['site_url']}index.html#{anchor}</guid>\n")
        rss.write(f"<description>{html.escape(description)}</description>\n")
        rss.write(f"<pubDate>{pub_date_str}</pubDate>\n")
        rss.write("</item>\n")

    rss.write("</channel>\n</rss>\n")

logging.info(f"RSS feed generated → {rss_file}")