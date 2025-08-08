# Notes Repository

This repository contains my notes written in Markdown, which are compiled into a single-page HTML file using a Python build script.

## Features

- Notes authored in Markdown with YAML front matter metadata.
- Single-page HTML output generated via a Python script.
- Cross-platform virtual environment setup for macOS and Windows.
- Git workflow guidelines for managing script development and backups.

## Directory Structure

```plaintext
|   apa.csl # Optional citation style file
|   build.py 
|   index.html 
|   README.md 
|   refs.json # Optional references file
|   requirements.txt # Python dependencies
|   typewriter.css 
+---.venv-mac # macOS virtual environment
+---.venv-win # Windows virtual environment
+---content # Markdown source files
|       2024-10-11-example.md     
+---fragments # Generated HTML fragments
|       2024-10-11-example.html  
```

## Setup Instructions

### macOS

```sh
python3 -m venv .venv-mac
source .venv-mac/bin/activate
pip install -r requirements.txt
```

### Windows

```powershell
python -m venv .venv-win
.venv-win\Scripts\activate
pip install -r requirements.txt
```

## Useful Aliases

`venv` toogles between activating and deactivating the virtual environment.

Add this to your shell config on macOS (`~/.zshrc` or `~/.bashrc`):

```sh
alias venv='if [ -n "$VIRTUAL_ENV" ]; then deactivate; else source .venv-mac/bin/activate; fi'
```

Add this to your PowerShell profile (`$PROFILE`) on Windows:

```powershell
Set-Alias venv 'if ($env:VIRTUAL_ENV) { deactivate } else { .\.venv-win\Scripts\Activate.ps1 }'
```

## Build

Generate the HTML page by running:

```sh
python .\build.py
```

This will produce `index.html` in the project directory.

## Git Workflow

1. Initialize the repository:

   ```sh
   git init
   ```

2. Commit a working script:

   ```sh
   git add build.py
   git commit -m "Working: generates single-page index.html"
   ```

3. Edit and test `build.py`. Commit changes if successful:

   ```sh
   git add build.py
   git commit -m "Describe your changes here"
   ```

4. If the script breaks, view commit history:

   ```sh
   git log --oneline
   ```

5. Restore `build.py` from a good commit:

   ```sh
   git checkout <commit-hash> -- build.py
   ```

6. Or reset the entire project to a previous state:

   ```sh
   git reset --hard <commit-hash>
   ```

7. Before risky changes, create a backup branch:

   ```sh
   git checkout -b backup-before-big-change
   ```

8. Work on new branches to isolate changes, and switch back to main if needed:

   ```sh
   git checkout main
   ```

## Adding Notes

1. Add or edit Markdown files in the `content` folder.
2. Use this file naming pattern: `YYYY-MM-DD-title.md`.
3. Each Markdown file should start with a YAML front matter block, for example:

   ```yaml
   ---
   title: Note Title
   description: A few things worth noting.
   tags:
     - tag1
     - tag2
   date: 2025-07-08
   ---
   ```

4. Run the build script to update `index.html`.
5. Open the generated `index.html` in a browser to verify your changes.
6. Commit your changes to the repository:

    ```sh
    git add content/
    git commit -m "Describe what changed"
    git push
    ```
