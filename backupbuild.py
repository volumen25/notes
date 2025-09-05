import os
import glob
import subprocess
import yaml
import re
import html
import sys

# Configuration
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
}

# Verify files and directory
for file in [CONFIG["css_file"], CONFIG["bib_file"], CONFIG["csl_file"]]:
    if not os.path.exists(file):
        print(f"Error: {file} not found.")
        exit(1)
if not os.path.isdir(CONFIG["content_dir"]):
    print(f"Error: '{CONFIG['content_dir']}' directory not found.")
    exit(1)
os.makedirs(CONFIG["frag_dir"], exist_ok=True)

# Process intro.md
intro_html = ""
if os.path.exists(CONFIG["intro_md"]):
    temp_md, output = os.path.join(CONFIG["frag_dir"], "intro.tmp.md"), os.path.join(
        CONFIG["frag_dir"], "intro.html"
    )
    with open(CONFIG["intro_md"], "r", encoding="utf-8") as src, open(
        temp_md, "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())
    try:
        subprocess.run(
            [
                "pandoc",
                temp_md,
                "-o",
                output,
                "--css",
                CONFIG["css_file"],
                "--no-highlight",
                "--file-scope",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        with open(output, "r", encoding="utf-8") as f:
            intro_html = f.read()
        os.remove(temp_md)
    except subprocess.CalledProcessError:
        pass

# Process Markdown files
md_files = sorted(
    [
        f
        for f in glob.glob(os.path.join(CONFIG["content_dir"], "*.md"))
        if not os.path.basename(f).startswith("README")
        and os.path.abspath(f) != os.path.abspath(CONFIG["intro_md"])
    ],
    reverse=True,
)

fragment_paths, toc_entries = [], []

# --- Progress bar settings ---
total_files = len(md_files)
bar_length = 30

for i, md_file in enumerate(md_files, start=1):
    # Calculate and display progress bar
    percent = i / total_files
    filled = int(bar_length * percent)
    bar = "#" * filled + "-" * (bar_length - filled)
    sys.stdout.write(
        f"\r[{bar}] {percent:>5.1%} ({i}/{total_files}) Processing {os.path.basename(md_file)}"
    )
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
    stem = os.path.splitext(os.path.basename(md_file))[0]
    temp_md, frag_html = os.path.join(
        CONFIG["frag_dir"], f"{stem}.tmp.md"
    ), os.path.join(CONFIG["frag_dir"], f"{stem}.html")
    fragment_paths.append(frag_html)

    with open(temp_md, "w", encoding="utf-8") as tmp:
        tmp.write(f"# {title} {{#{anchor}}}\n{date}\n\n{body}\n\n::: {{#refs}}\n:::\n")
    try:
        subprocess.run(
            [
                "pandoc",
                temp_md,
                "-o",
                frag_html,
                "--css",
                CONFIG["css_file"],
                "--no-highlight",
                "--citeproc",
                "--file-scope",
                f"--bibliography={CONFIG['bib_file']}",
                f"--csl={CONFIG['csl_file']}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        os.remove(temp_md)
    except subprocess.CalledProcessError:
        continue

# Ensure progress bar line is cleared
print()

# Assemble HTML
with open(CONFIG["final_html"], "w", encoding="utf-8") as index:
    index.write(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="generator" content="{CONFIG['generator']}">
    <meta name="viewport" content="{CONFIG['viewport']}">
    <title>{CONFIG['title']}</title>
    <link rel="icon" type="image/x-icon" href="favicon.ico">
    <link rel="stylesheet" href="{CONFIG['css_file']}">
</head>
<body>
    <h1>{CONFIG['title']}</h1>
    {intro_html + '\n<hr>\n' if intro_html else ''}
"""
    )
    for frag_path in fragment_paths:
        if os.path.exists(frag_path):
            with open(frag_path, "r", encoding="utf-8") as frag:
                index.write(frag.read() + "\n<hr>\n")
    index.write("<h1>Index</h1>\n<ul>\n")
    for title, anchor in toc_entries:
        index.write(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>\n')
    index.write("</ul>\n</body>\n</html>\n")

print(f"Page generated → {CONFIG['final_html']}")
