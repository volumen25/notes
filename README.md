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

## Short Aliases

macOS shell config (.zshrc or .bashrc):

```sh
alias venv='if [ -n "$VIRTUAL_ENV" ]; then deactivate; else source .venv-mac/bin/activate; fi'
```

Windows PowerShell profile ($PROFILE):

```ps1
Set-Alias venv 'if ($env:VIRTUAL_ENV) { deactivate } else { .\.venv-win\Scripts\Activate.ps1 }'
```
