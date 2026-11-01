# Image de build BSB-LAN pour ESP32-C3 : arduino-cli et core esp32 figés.
# Construite par docker/compiler.sh ; documentation : docs/claude/README_docker.md.
FROM debian:trixie-slim

ARG ARDUINO_CLI_VERSION=1.3.1
ARG ARDUINO_CLI_SHA256=376428d7d45be640c00812a71612e1742edc2f5f9ee3742a2d6da7870e079588
ARG ESP32_CORE_VERSION=3.3.12

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl python3 \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/arduino-cli.tar.gz \
      "https://github.com/arduino/arduino-cli/releases/download/v${ARDUINO_CLI_VERSION}/arduino-cli_${ARDUINO_CLI_VERSION}_Linux_64bit.tar.gz" \
 && echo "${ARDUINO_CLI_SHA256}  /tmp/arduino-cli.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/arduino-cli.tar.gz -C /usr/local/bin arduino-cli \
 && rm /tmp/arduino-cli.tar.gz

ENV ARDUINO_DIRECTORIES_DATA=/opt/arduino \
    ARDUINO_DIRECTORIES_USER=/opt/arduino/user \
    ARDUINO_DIRECTORIES_DOWNLOADS=/opt/arduino/staging \
    ARDUINO_NETWORK_CONNECTION_TIMEOUT=1800s

# La chaîne RISC-V pèse ~560 Mo : délai réseau allongé et 3 tentatives (les archives déjà reçues sont réutilisées).
RUN arduino-cli core update-index \
 && for essai in 1 2 3; do \
      arduino-cli core install "esp32:esp32@${ESP32_CORE_VERSION}" --no-color > /dev/null && break; \
      echo "tentative $essai échouée"; [ "$essai" = 3 ] && exit 1; \
    done \
 && rm -rf /opt/arduino/staging \
 && chmod -R a+rX /opt/arduino

LABEL org.opencontainers.image.description="BSB-LAN build: arduino-cli ${ARDUINO_CLI_VERSION}, esp32 ${ESP32_CORE_VERSION}"
