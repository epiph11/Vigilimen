#!/bin/sh
# Runs INSIDE an OpenPLC container (it has iec2c and g++). Called by replay-safety.ps1.
# Compiles safety_upload.st to C with MatIEC, builds safety_replay.cpp against it, replays the vectors.
cd /workdir/webserver || exit 2
rm -rf /tmp/replay/gen && mkdir -p /tmp/replay/gen
./iec2c -f -l -p -r -R -a -T /tmp/replay/gen /tmp/replay/safety_upload.st > /tmp/replay/iec2c.log 2>&1 || { cat /tmp/replay/iec2c.log; echo "IEC2C FAILED"; exit 3; }
# GENERATED directory FIRST: core/ holds the POUS.h of whatever was last compiled for real.
# replay_stubs.cpp: OpenPLC's TCP function blocks (never used by safety.st) call functions the PLC runtime provides.
g++ -std=gnu++11 -w -fpermissive -I /tmp/replay/gen -I /workdir/webserver/core/lib -I /workdir/webserver/core \
    /tmp/replay/safety_replay.cpp /tmp/replay/replay_stubs.cpp -o /tmp/replay/replay > /tmp/replay/gpp.log 2>&1 || { head -40 /tmp/replay/gpp.log; echo "G++ FAILED"; exit 4; }
/tmp/replay/replay < /tmp/replay/vectors.csv
