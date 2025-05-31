# 1. Basis-Image mit Python 3.10 oder höher
FROM python:3.11-slim

# 2. Arbeitsverzeichnis setzen
WORKDIR /app

# 3. Systemabhängigkeiten installieren (falls benötigt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Python-Abhängigkeiten installieren
# requirements.txt wird weiter unten beschrieben
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. App-Code kopieren
COPY app.py .
#COPY .env .env

# 6. Exponiere den Gradio-Port
EXPOSE 7860

# 7. Startbefehl
CMD ["python", "app.py"]
