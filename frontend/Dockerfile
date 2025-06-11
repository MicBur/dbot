# Verwende ein offizielles Node.js-Image als Basis
FROM node:18-alpine

# Verhindere, dass npm Fortschrittsbalken ausgibt, die die Logs unübersichtlich machen können
ENV NPM_CONFIG_LOGLEVEL=warn

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere package.json und package-lock.json (oder yarn.lock)
COPY package*.json ./

# Installiere die Abhängigkeiten
RUN npm install

# Kopiere den Rest des Anwendungscodes
# (Dies wird durch das Volume in docker-compose.yml für die Entwicklung überschrieben,
# ist aber gut für den Build-Kontext und für Produktions-Builds)
COPY . .

# Exponiere den Port, auf dem Next.js läuft
EXPOSE 3000

# Starte die Next.js Entwicklungs-Server
CMD ["npm", "run", "dev"]