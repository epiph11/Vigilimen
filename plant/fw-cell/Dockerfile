# fw-cell - the cell firewall (ADR-023, point 1; physical: firewall C, BOM-021).
# Build context is plant/ , like the other services.
#   docker compose build fw-cell
#
# nftables for the policy, socat for the relay. See entrypoint.sh for what it does
# and for what it cannot show (a container is not a DIN-rail appliance).
FROM alpine:3.20

RUN apk add --no-cache nftables socat su-exec musl-utils

COPY fw-cell/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY fw-cell/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod 0555 /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

EXPOSE 4840

# Healthy = the policy table is loaded AND the relay's far side (the gateway) answers.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/usr/local/bin/healthcheck.sh"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
