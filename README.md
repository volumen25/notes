# Notes Repository

This repository contains my notes written in Markdown, which are compiled into a single-page HTML file and an RSS feed using a Python static site generator.

## Features

- Notes authored in Markdown with YAML front matter metadata
- Single-page HTML output with automatic table of contents
- RSS feed automatically generated for the 20 most recent notes
- Citation support using CSL and BibTeX
- Parallel processing for faster builds
- Automatic content synchronization from source directory

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.14+**
- **uv** - Python package manager ([installation guide](https://github.com/astral-sh/uv))
- **Pandoc** - Document converter ([installation guide](https://pandoc.org/installing.html))

  ```bash
  # macOS (via Homebrew)
  brew install pandoc
  
  # Ubuntu/Debian
  sudo apt-get install pandoc
  
  # Fedora
  sudo dnf install pandoc
  
  # Or download from https://pandoc.org/installing.html
  ```

## Directory Structure

```plaintext
notes/                          # Project root
├── assets/
│   ├── apa.csl                # Citation style (APA format)
│   ├── favicon.ico            # Site favicon
│   ├── md-to-html-links.lua   # Pandoc Lua filter
│   ├── refs.json              # Bibliography file
│   └── typewriter.css         # Site stylesheet
├── CNAME                       # Custom domain (for GitHub Pages)
├── content/                    # Markdown notes (generated from source)
│   ├── 2022-07-15-Truth-vs-BS.md
│   ├── colophon.md            # Optional colophon (appears at bottom)
│   └── intro.md               # Optional intro text (appears first)
├── docs/                       # Generated output (GitHub Pages ready)
│   ├── favicon.ico
│   ├── index.html
│   ├── rss.xml
│   └── typewriter.css
├── ssg/                        # Build system
│   ├── __init__.py
│   ├── build.py               # Main build script
│   └── fragments/             # Temporary HTML fragments (generated)
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
└── README.md
```

## Setup Instructions

1. **Clone the repository and initialize uv:**

   ```bash
   cd notes
   uv init
   ```

2. **Install dependencies:**

   ```bash
   uv add "PyYAML>=6.0"
   uv add --dev black
   ```

   This will:
   - Create a `.venv` virtual environment in the project root
   - Install dependencies defined in `pyproject.toml`

3. **Configure source directory (if needed):**

   The build script copies Markdown files from a source directory. By default, it looks for:

   ```txt
   ~/Documents/codeberg/content
   ```

   Edit `ssg/build.py` line 84 to change this location:

   ```python
   SOURCE_DIR = Path.home() / "Documents/codeberg/content"  # Change this path
   ```

## Project Configuration

The `pyproject.toml` file should contain:

```toml
[project]
name = "notes"
version = "0.1.0"
description = "Custom SSG"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "pyyaml>=6.0",
]

[project.scripts]
build = "ssg.build:main"

[tool.uv]
package = true

[dependency-groups]
dev = [
    "black>=25.12.0",
]

[tool.black]
line-length = 88
target-version = ["py314"]

[tool.setuptools.packages.find]
include = ["ssg*"]
```

## Writing Notes

### Creating a New Note

1. **Create a Markdown file** in your source directory (`~/Documents/codeberg/content` or your configured path)

2. **Add YAML front matter** with required metadata:

   ```yaml
   ---
   title: Your Note Title
   date: 2025-01-05
   tags:
     - volumen
     - other-tag
   ---
   
   Your note content goes here...
   ```

3. **Important requirements:**
   - The `tags` field **must include "volumen"** for the note to be included in the build
   - The `date` field should be in `YYYY-MM-DD` format
   - The `title` field is required (defaults to "Untitled" if missing)

### File Naming Convention

While not strictly required (dates come from YAML frontmatter), the recommended pattern is:

```txt
YYYY-MM-DD-descriptive-title.md
```

Examples:

- `2025-01-05-my-first-note.md`
- `2024-12-15-year-end-review.md`

### Special Files

- **`intro.md`**: Optional file that appears at the top of the generated page (after the site title, before notes). It should not have YAML frontmatter.

- **`colophon.md`**: Optional file that appears at the bottom of the generated page (after all notes, before the Index/ToC). It should not have YAML frontmatter. Use this for site information, credits, or technical details.

## Building the Site

### Standard Build

```bash
uv run build
```

This will:

1. Copy Markdown files tagged with "volumen" from source to `content/`
2. Process `intro.md` (if exists) for top of page
3. Convert each regular Markdown file to HTML using Pandoc
4. Process `colophon.md` (if exists) for bottom of page
5. Generate a single `docs/index.html` with all content
6. Create an RSS feed (`docs/rss.xml`) with the 20 most recent notes
7. Copy assets (CSS, favicon) to `docs/`

### Development Workflow

```bash
# Sync dependencies after configuration changes
uv sync

# Format code (if you modified build.py)
uv run black .

# Build the site
uv run build
```

### Viewing Your Site

After building, open the generated site in your browser:

```bash
# macOS
open docs/index.html

# Linux
xdg-open docs/index.html

# Or use a local server
python3 -m http.server 8000 --directory docs
# Then visit http://localhost:8000
```

## How It Works

1. **Content Synchronization**: The build script scans your source directory for Markdown files tagged with "volumen" and copies them to `content/`

2. **Markdown Processing**: Each note is processed by Pandoc with:
   - Citation support (using `refs.json` and `apa.csl`)
   - Syntax highlighting disabled
   - Custom Lua filter for link conversion
   - File scope isolation

3. **HTML Generation**: All processed notes are combined into a single `index.html` with:
   - Optional intro section at the top (from `intro.md`)
   - Notes sorted by date (newest first)
   - Optional colophon section at the bottom (from `colophon.md`)
   - Automatic table of contents at the very bottom
   - Custom CSS styling

4. **RSS Feed**: The 20 most recent notes are included in `rss.xml` with descriptions automatically extracted from the second paragraph of each note

## Citations and Bibliography

The build system supports citations using:

- **refs.json**: Your bibliography in CSL JSON format
- **apa.csl**: Citation Style Language file (APA format)

Use citations in your Markdown like:

```markdown
According to recent research [@smith2024], we can see that...
```

## Deployment

### GitHub Pages

The `docs/` directory is configured for GitHub Pages:

1. Push your repository to GitHub
2. Go to Settings → Pages
3. Select "Deploy from a branch"
4. Choose `main` branch and `/docs` folder
5. Your site will be published at `https://username.github.io/repository-name/`

### Custom Domain

If you have a custom domain, create a `CNAME` file in the root:

```txt
yourdomain.com
```

## Troubleshooting

### "pandoc: command not found"

Install Pandoc using your package manager (see Prerequisites).

### "No Markdown files found in content directory"

- Check that your source directory path is correct in `build.py`
- Ensure your Markdown files have the "volumen" tag in their YAML frontmatter

### Notes not appearing on the site

- Verify the file has YAML frontmatter with `tags: [volumen]` or `tags: - volumen`
- Check that the file was copied to the `content/` directory
- Run the build with increased logging to see errors

### RSS feed not updating

- The RSS feed only includes the 20 most recent notes
- Check that your notes have valid dates in YAML frontmatter
- Clear your RSS reader's cache

### Build errors with citations

- Ensure `assets/refs.json` exists and is valid JSON
- Verify citation keys in your Markdown match entries in `refs.json`

## Development

To modify the build script:

1. Edit `ssg/build.py`
2. Format with Black: `uv run black .`
3. Test your changes: `uv run build`
