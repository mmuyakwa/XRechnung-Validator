# Schritt 1: Erstelle eine Python Virtual Environment in einem Ordner namens '.venv'
C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv

# Schritt 2: Aktiviere die virtuelle Umgebung
. .\.venv\Scripts\Activate.ps1

# Schritt 3: Aktualisiere `pip` und installiere die Pakete `wheel` und `python-dotenv` mit der Option `--upgrade`
pip install --upgrade pip
pip install --upgrade wheel python-dotenv autopep8 mkdocs

# Schritt 3: Installiere die erforderlichen Python-Pakete
# Wenn eine requirements.txt-Datei vorhanden ist, installiere die darin aufgelisteten Pakete
if (Test-Path -Path "requirements.txt") {
    pip install -r requirements.txt
}

# Schritt 4: Initialisiere `mkdocs` mit dem Namen des aktuellen Verzeichnisses
mkdocs new (Split-Path -Leaf -Path (Get-Location))
# Erstelle eine Konfigurationsdatei für `mkdocs`. Übergebe den Namen des aktuellen Verzeichnisses als `site_name`
Set-Content -Path "mkdocs.yml" -Value "site_name: $(Split-Path -Leaf -Path (Get-Location))"
# Füge das Theme `readthedocs` zur Konfigurationsdatei hinzu
Add-Content -Path "mkdocs.yml" -Value "theme: readthedocs"

# Gib eine Nachricht aus, die darauf hinweist, dass das Skript abgeschlossen ist
Write-Host "Entwicklungsumgebung wurde eingerichtet."

$PWD.Path | Out-File -FilePath location.txt
