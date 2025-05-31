# **Projekt-Dokumentation: XRechnung-Validator-Umgebung**

## **Projektübersicht**

Dieses Projekt besteht aus einer Docker-basierten Umgebung zur Validierung und Analyse von XRechnungen (elektronischen Rechnungen nach dem deutschen XRechnung-Standard). Es kombiniert zwei Hauptkomponenten:

1. **XRechnung-Validator**: Eine Java-basierte Anwendung, die XML-Dokumente gegen den XRechnung-Standard validiert  
2. **XRechnung-Prüfer**: Eine Python-basierte Anwendung, die mithilfe von KI (Anthropic's Claude) XRechnungen analysiert und Fehler korrigiert

Diese Anleitung beschreibt, wie du die vorgefertigten Docker-Images von Docker Hub verwenden kannst, anstatt die Images selbst zu bauen.

## **Was ist der XRechnung-Validator?**

Der XRechnung-Validator ist ein Werkzeug, das prüft, ob eine elektronische Rechnung dem XRechnungs-Standard entspricht. Einfach ausgedrückt, er stellt sicher, dass die Rechnung alle notwendigen Informationen im richtigen Format enthält. Dieses Tool wurde in diesem Docker-Container integriert, um XRechnung-Dateien zu validieren. Die Validierungsdateien für XRechnung 3.0.2 werden hierfür genutzt.

Weitere Informationen zu diesem Validator-Tool findest du im [ursprünglichen GitHub-Projekt](https://github.com/itplr-kosit/validator-configuration-xrechnung) sowie auf [Docker Hub](https://hub.docker.com/repository/docker/mmuyakwa/xrvalidate/general) (dem Docker Hub-Repository des XRechnung-Validators).

## **Was ist der XRechnung-Prüfer?**

Der XRechnung-Prüfer ist eine Python-Anwendung, die KI einsetzt, um XRechnungen zu analysieren und Fehler zu korrigieren. Sie nimmt XML-Rechnungen und Fehlermeldungen als Eingabe, analysiert die Fehler und versucht, eine korrigierte XML-Version der Rechnung zu erstellen. Das zugehörige Docker Hub-Repository findest du [hier](https://hub.docker.com/repository/docker/mmuyakwa/xrechnung-check).

## **Voraussetzungen**

Stelle sicher, dass Docker und Docker Compose auf deinem System installiert sind.

* **Docker:** [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)  
* **Docker Compose:** [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/)

## **Installation und Verwendung**

### **Docker Compose Datei erstellen**

Erstelle eine Datei namens docker-compose.yaml mit folgendem Inhalt:

```yaml
version: "3.8"

services:  
  xrechnung-validator:  
    image: mmuyakwa/xrvalidate:3.0.2  
    container_name: xrechnung-validator  
    hostname: xrechnung-validator  
    ports:  
      - "8080:8080"  
    restart: unless-stopped  
    volumes:  
      - ./xrechnung-config:/app/xrechnung-config # Erstelle diesen Ordner lokal. Die benötigten Dateien können von https://github.com/itplr-kosit/validator-configuration-xrechnung/releases heruntergeladen werden.  
    environment:  
      TZ: Europe/Berlin # Setzt die Zeitzone auf Berlin  
    networks:  
      - xrechnung-network

  xrechnung-pruefer:  
    image: mmuyakwa/xrechnung-check:3.0.2  
    container_name: xrechnung-pruefer  
    hostname: xrechnung-pruefer  
    depends_on:  
      - xrechnung-validator  
    env_file:  
      - .env # Erstelle diese Datei mit deinem Anthropic API-Schlüssel  
    ports:  
      - "7860:7860"  
    restart: unless-stopped  
    networks:  
      - xrechnung-network

networks:  
  xrechnung-network:  
    driver: bridge
```

**Hinweis:** Erstelle einen Ordner namens xrechnung-config im selben Verzeichnis wie deine docker-compose.yaml-Datei. Dieser Ordner wird benötigt, damit der xrechnung-validator ordnungsgemäß funktioniert. Du kannst den Ordnerinhalt aus dem ursprünglichen Projekt-Repository kopieren, oder ein leeres Verzeichnis erstellen, falls du eigene Konfigurationsdateien verwenden möchtest.

### **.env-Datei erstellen**

Erstelle eine Datei namens .env im selben Verzeichnis wie deine docker-compose.yaml-Datei aus. Füge deinen Anthropic API-Schlüssel und die Validator-Host-Informationen hinzu:

```plaintext
ANTHROPIC_API_KEY=your_anthropic_api_key  
VALIDATOR_HOST="xrechnung-validator"  
VALIDATOR_PORT=8080
```

Ersetze your_anthropic_api_key durch deinen tatsächlichen API-Schlüssel.

### **Container starten**

Führe den folgenden Befehl im selben Verzeichnis wie deine docker-compose.yaml-Datei aus:

docker-compose up -d

Dieser Befehl lädt die angegebenen Images von Docker Hub herunter (falls nicht bereits lokal vorhanden) und startet die Container im Hintergrund.

### **Anwendungen aufrufen**

* **XRechnung-Validator:** Öffne deinen Webbrowser und gehe zu http://localhost:8080.  
* **XRechnung-Prüfer:** Öffne deinen Webbrowser und gehe zu http://localhost:7860.