# pki-init - one-shot: writes the lab certificates into the `pki` volume, one folder per service.
# Lab self-signed certificates only (see uasec.py for what this is not). Build context is plant/.
FROM python:3.12-slim
RUN pip install --no-cache-dir --root-user-action=ignore "cryptography==50.0.2"
WORKDIR /opt/vigilimen
COPY pki/uasec.py /opt/vigilimen/uasec.py
COPY pki/mqttpki.py /opt/vigilimen/mqttpki.py
# Runs as root on purpose: it owns the volume and hands each folder to the uid of its service.
# Two separate trust models, two volumes: OPC UA allow-list (uasec.py) and the MQTT lab CA (mqttpki.py).
CMD ["sh", "-c", "python3 uasec.py init /pki && python3 mqttpki.py init /pki-mqtt"]
