# CONV-001 collector — OPC UA client, TimescaleDB writer.
#
#   docker compose build collector
#
# Build context is plant/historian/. Unlike the gateway this container needs
# nothing from sim/ — it reads the plant over the wire like any other client,
# which is the property that makes it replaceable.

FROM python:3.12-slim

RUN useradd --create-home --uid 10002 collector

WORKDIR /opt/mined

RUN pip install --no-cache-dir --root-user-action=ignore \
        "asyncua==1.1.5" \
        "psycopg[binary]==3.2.3"

COPY collector.py /opt/mined/collector.py

USER collector

# TZ is set to UTC in compose and the code stamps tz-aware UTC regardless.
# Both, deliberately: the environment variable is a convenience for anyone
# who exec's into the container, and the code does not trust it (ADR-010).
ENV PYTHONUNBUFFERED=1

# No EXPOSE. This container listens on nothing. It is a client at both ends,
# and a container with no listening socket is a container with no remotely
# reachable attack surface — worth noticing, because it is rare.

CMD ["python3", "collector.py"]
