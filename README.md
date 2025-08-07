# Notes

## On macOS

```md
python3 -m venv .venv-mac
source .venv-mac/bin/activate
pip install -r requirements.txt
```

## On Windows

```md
python -m venv .venv-win
.venv-win\Scripts\activate
pip install -r requirements.txt
```

## Optional: Tiny Launcher scripts

Create a .activate file or Makefile on macOS:

```md
# activate-mac.sh
source .venv-mac/bin/activate
```

And a .bat file on Windows:

```md
:: activate-win.bat
.venv-win\Scripts\activate
```
