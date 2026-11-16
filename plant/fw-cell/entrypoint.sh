#!/bin/sh
# fw-cell - the single door of the cell (ADR-023, flows F8, F9, F10).
#
# WHAT IT DOES
#   * Listens on 4840 on the supervisory leg and relays to the gateway (net_control side).
#   * nftables, default deny. Only two sources may open the relay:
#       FW-CELL-001  opcua-sup -> gateway:4840   the read path (F8)
#       FW-CELL-002  scada     -> gateway:4840   the operator command path (F9)
#     Everything else is counted and the source is recorded (FW-CELL-DEFAULT).
#   * Nothing is routed: the forward chain is policy drop and ip_forward is 0.
#   * Every few seconds it prints the counters and the sources it dropped (F10, FW-CELL-003).
#     `docker logs vigilimen-fw-cell` is the evidence. A per-packet kernel log is not used:
#     Linux does not log from a container's network namespace by default.
#
# WHAT IT CANNOT SHOW (ADR-023, Consequences)
#   * It cannot tell a read from a write: both are OPC UA on 4840. The only writer path stays
#     a known target (R-14, S8). The rule names WHO may use the door, not WHAT they say.
#   * The gateway sees fw-cell as the source, not scada or opcua-sup. OPC UA accounts still
#     tell them apart (attribution, ADR-017).
#   * A container is not a DIN-rail appliance: this shows the policy, not the device.
set -eu

LISTEN_PORT="${FW_LISTEN_PORT:-4840}"
UPSTREAM_HOST="${FW_UPSTREAM_HOST:-gateway}"
UPSTREAM_PORT="${FW_UPSTREAM_PORT:-4840}"
F8_SRC="${FW_F8_SOURCE:-opcua-sup}"
F9_SRC="${FW_F9_SOURCE:-scada}"

nft -f - <<NFT
table inet fwcell {
  set f8 { type ipv4_addr; }
  set f9 { type ipv4_addr; }
  set seen { type ipv4_addr; flags dynamic,timeout; timeout 10m; }
  counter c_f8 { }
  counter c_f9 { }
  counter c_drop { }
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
    tcp dport ${LISTEN_PORT} ip saddr @f8 ct state new counter name c_f8 accept comment "FW-CELL-001"
    tcp dport ${LISTEN_PORT} ip saddr @f9 ct state new counter name c_f9 accept comment "FW-CELL-002"
    update @seen { ip saddr } counter name c_drop drop comment "FW-CELL-DEFAULT"
  }
  chain forward { type filter hook forward priority 0; policy drop; }
  chain output  { type filter hook output priority 0; policy accept; }
}
NFT

# The relay runs unprivileged. Binding a port above 1024 needs no capability.
su-exec nobody:nobody socat "TCP-LISTEN:${LISTEN_PORT},fork,reuseaddr" "TCP:${UPSTREAM_HOST}:${UPSTREAM_PORT}" &
RELAY=$!
echo "fw-cell: relay :${LISTEN_PORT} -> ${UPSTREAM_HOST}:${UPSTREAM_PORT}; FW-CELL-001 from ${F8_SRC}, FW-CELL-002 from ${F9_SRC}, everything else dropped"

resolve() {            # first IPv4 of a service name, or nothing
  getent hosts "$1" 2>/dev/null | awk 'NR==1 && $1 ~ /^[0-9.]+$/ {print $1}'
}
fill() {               # set name, host name
  ip="$(resolve "$2")"
  # One transaction: flush + add are applied together, so there is no instant with an empty
  # set (a separate flush then add dropped opcua-sup's own packet once, seen in the first run).
  if [ -n "$ip" ]; then
    printf 'flush set inet fwcell %s\nadd element inet fwcell %s { %s }\n' "$1" "$1" "$ip" | nft -f -
  else
    nft flush set inet fwcell "$1"
  fi
  echo "$ip"
}
count() {              # counter name -> packets
  nft list counter inet fwcell "$1" | awk '/packets/ {print $2}'
}

last=""
# Not `kill -0`: the entrypoint has no CAP_KILL (cap_drop ALL) and the relay runs as another uid,
# so kill -0 fails with EPERM even while the relay is alive. /proc needs no capability.
while [ -d "/proc/$RELAY" ]; do
  a="$(fill f8 "$F8_SRC")"; b="$(fill f9 "$F9_SRC")"
  now="f8=${a:-unresolved} f9=${b:-unresolved} FW-CELL-001=$(count c_f8) FW-CELL-002=$(count c_f9) FW-CELL-DEFAULT_drops=$(count c_drop) dropped_sources=[$(nft list set inet fwcell seen | tr -d '\n\t' | sed -n 's/.*elements = {\(.*\)}.*/\1/p')]"
  if [ "$now" != "$last" ]; then echo "fw-cell: $now"; last="$now"; fi
  sleep 5
done
echo "fw-cell: relay exited" >&2
exit 1
