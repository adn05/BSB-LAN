#!/bin/sh
# Compile le firmware Alféa dans Docker. Usage, depuis la racine du dépôt : sh docker/compiler.sh
# Sortie : alfea/build/alfea. Documentation : docs/claude/README_docker.md
set -eu
IMAGE=bsblan-build:cli-1.3.1-esp32-3.3.12
DEPOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$DEPOT/docker/arduino-cli"
case "$(uname -s)" in MINGW*|MSYS*) DEPOT="$(cygpath -w "$DEPOT")"; CTX="$(cygpath -w "$CTX")"; export MSYS_NO_PATHCONV=1 ;; esac
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker build -t "$IMAGE" "$CTX"
docker run --rm -e HOME=/tmp -e ARDUINO_DIRECTORIES_DOWNLOADS=/tmp/arduino-staging --user "$(id -u):$(id -g)" -v "$DEPOT:/work" "$IMAGE" sh /work/docker/build.sh
