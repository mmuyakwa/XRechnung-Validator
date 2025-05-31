FROM openjdk:17-jdk-slim

LABEL org.opencontainers.image.authors="Michael Muyakwa <mm@secion.de>"
LABEL org.opencontainers.image.description="XRechnung Validator auf Basis KoSIT 1.5.0"

ENV LANG=C.UTF-8
ENV JAVA_HOME=/usr/local/openjdk-17
ENV JAVA_VERSION=17
ENV PATH="$JAVA_HOME/bin:$PATH"

# Optional: curl für Healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY validationtool-1.5.0-standalone.jar /app/validator.jar
COPY xrechnung-config /app/xrechnung-config

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/ || exit 1

CMD ["/usr/local/openjdk-17/bin/java", "-jar", "validator.jar", "-s", "/app/xrechnung-config/scenarios.xml", "-r", "/app/xrechnung-config", "-D", "-H", "0.0.0.0"]
