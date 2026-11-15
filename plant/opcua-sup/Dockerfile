# opcua-sup - read-only supervisory OPC UA server (ADR-023).
# Build context is plant/ , like the gateway and the collector.
#   docker compose build opcua-sup
FROM python:3.12-slim

RUN useradd --create-home --uid 10003 opcuasup
WORKDIR /opt/vigilimen
RUN pip install --no-cache-dir --root-user-action=ignore "asyncua==1.1.5"

COPY opcua-sup/opcua_sup.py   /opt/vigilimen/opcua_sup.py
COPY opcua-sup/healthcheck.py /opt/vigilimen/healthcheck.py

USER opcuasup
ENV PYTHONUNBUFFERED=1
EXPOSE 4840

# A session that returns GOOD data, not a bare TCP check: see healthcheck.py.
HEALTHCHECK --interval=15s --timeout=6s --start-period=15s --retries=3 \
  CMD ["python3", "healthcheck.py"]

CMD ["python3", "opcua_sup.py", "--port", "4840"]
