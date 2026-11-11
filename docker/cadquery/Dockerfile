# CAO du boîtier de la carte d'interface (CadQuery, versions figées). Usage : docker/cadquery/boitier.sh
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxrender1 libxext6 libsm6 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --retries 5 --timeout 120 cadquery==2.5.2 cadquery-ocp==7.7.2 numpy==2.4.6 matplotlib==3.11.2 casadi==3.8.2 nlopt==2.11.0 ezdxf==1.4.5
WORKDIR /travail
