# FUXA with its OPC UA driver baked in (16 Nov 2026).
#
# WHY: the stock FUXA image ships without the OPC UA driver (node-opcua) and installs it from the
# Internet when a person clicks Install on the Plugins page. That worked in Sprint 4 only because
# net_supervisory had an Internet route; since ADR-023 it is internal, and a container recreate deletes
# a runtime install anyway. A SCADA that downloads software at runtime is also a supply-chain gap
# (FF-20), so the driver is installed here, at build time, at a pinned version.
#
# The base is pinned by the digest of the image used in Sprint 4 and in the 16 Nov run
# (`docker images --digests frangoteam/fuxa`, created about 3 weeks before 16 Nov 2026).
# node-opcua 2.149.0 is the version FUXA's Plugins page offers for this image.
#
#   docker compose build scada
FROM frangoteam/fuxa@sha256:9b1dfbe9280319c742e3fe97674f7b9692a2b2d68546a42f6ea89960eecefeb5

# FUXA keeps its server code under /usr/src/app/FUXA/server (the compose volumes mount into it).
WORKDIR /usr/src/app/FUXA/server
RUN npm install --no-audit --no-fund node-opcua@2.149.0 \
 && test -f node_modules/node-opcua/package.json \
 && node -e "console.log('node-opcua', require('node-opcua/package.json').version)"
