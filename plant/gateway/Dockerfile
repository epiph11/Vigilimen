# CONV-001 gateway — the protocol break.
#
# Build context is plant/ , NOT plant/gateway/ , because the gateway imports
# the simulation modules from ../sim. A Dockerfile cannot COPY above its own
# context, and the usual reflex — copy sim/ into gateway/ — would leave two
# divergent copies of the physics model within a month.
#
#   docker compose build gateway
#
# ---------------------------------------------------------------------------
# Pinned by digest-less tag on purpose: this is a local simulation, and a
# floating patch level is an acceptable trade for a readable file. A real
# OT image is pinned by digest and rebuilt on a schedule, which is the
# 62443-4-1 SM-9 obligation, not a preference.
# ---------------------------------------------------------------------------

FROM python:3.12-slim

# Non-root. There is nothing in this container worth escalating to, which is
# the reason people skip it, and skipping it is how a container image gets
# copied into something that does.
RUN useradd --create-home --uid 10001 gateway

WORKDIR /opt/limen

# Dependencies first, so a change to the plant code does not re-resolve pip.
RUN pip install --no-cache-dir --root-user-action=ignore \
        "asyncua==1.1.5"

COPY sim/     /opt/limen/sim/
COPY gateway/ /opt/limen/gateway/

USER gateway

# 4840 is the IANA-registered OPC UA port. Inside the container it is 4840;
# compose publishes it on 127.0.0.1:14840 so it cannot collide with a local
# install and cannot be reached from the network.
EXPOSE 4840

# No HEALTHCHECK that merely proves the process is alive. A TCP listener that
# accepts and answers nothing is the exact failure this stack is meant to
# make visible, so the check opens a session.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "\
import asyncio,sys;\
from asyncua import Client;\
\
async def m():\
    c = Client('opc.tcp://127.0.0.1:4840/limen/conv001/');\
    c.set_user('historian'); c.set_password('h1st0r1an-demo');\
    await c.connect();\
    await c.disconnect();\
\
sys.exit(0 if not asyncio.run(m()) else 1)" || exit 1

CMD ["python3", "gateway/opcua_server.py", "--port", "4840"]

# ---------------------------------------------------------------------------
# WHAT THIS CONTAINER IS NOT, YET.
#
# It runs the physics and interlock models in-process and serves them over
# OPC UA. It does NOT read the OpenPLC runtime over Modbus — LIMEN_MODBUS_HOST
# is set in compose and is not consumed here.
#
# That gap is real and is named rather than hidden: closing it is S5 work
# (`gateway/modbus.py` already speaks the wire format). Until then the two
# OpenPLC containers exist so that logic can be downloaded to them from an
# engineering workstation, which is the attack path S8 needs, and the OPC UA
# values come from the simulation.
# ---------------------------------------------------------------------------
