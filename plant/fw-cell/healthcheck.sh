#!/bin/sh
# Policy loaded, relay listening, gateway answering on the far side.
nft list table inet fwcell >/dev/null 2>&1 || exit 1
nc -z -w 2 127.0.0.1 "${FW_LISTEN_PORT:-4840}" || exit 1
nc -z -w 2 "${FW_UPSTREAM_HOST:-gateway}" "${FW_UPSTREAM_PORT:-4840}" || exit 1
