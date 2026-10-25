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

WORKDIR /opt/vigilimen

# Dependencies first, so a change to the plant code does not re-resolve pip.
RUN pip install --no-cache-dir --root-user-action=ignore \
        "asyncua==1.1.5"

COPY sim/     /opt/vigilimen/sim/
COPY gateway/ /opt/vigilimen/gateway/

USER gateway

# 4840 is the IANA-registered OPC UA port. Inside the container it is 4840;
# compose publishes it on 127.0.0.1:14840 so it cannot collide with a local
# install and cannot be reached from the network.
EXPOSE 4840

# No HEALTHCHECK that merely proves the process is alive. A TCP listener that
# accepts and answers nothing is the exact failure this stack is meant to
# make visible, so the check opens a session.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python3", "gateway/healthcheck.py"]

CMD ["python3", "gateway/opcua_server.py", "--port", "4840"]

# ---------------------------------------------------------------------------
# TWO MODES (ADR-013).
#
# Default: the physics and interlock models run in-process and are served over
# OPC UA; the OpenPLC containers run beside the plant and decide nothing.
#
# VIGILIMEN_PLC_LINK=modbus (set by docker-compose.plcio.yml): this container
# plays the field and drives PLC-CONV-001 over Modbus (gateway/plc_link.py), and
# the motor turns only if the safety-contactor model is energised AND the PLC
# requests run. It stays opt-in until FF-26 has passed against real OpenPLC.
# ---------------------------------------------------------------------------
