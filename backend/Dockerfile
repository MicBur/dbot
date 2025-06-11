# Verwende ein offizielles Python-Image als Basis
FROM python:3.10-slim

# Verhindere, dass Python .pyc Dateien schreibt und deaktiviere Pufferung für stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die requirements.txt Datei (wird später erstellt)
COPY requirements.txt ./

# Installiere die Abhängigkeiten (wird später angepasst)
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest des Anwendungscodes
COPY . .

# Exponiere den Port, auf dem die App läuft (muss mit dem Port in uvicorn übereinstimmen)
EXPOSE 8000

# Starte die Anwendung
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]