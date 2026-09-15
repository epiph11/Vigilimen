# FUXA project directory

This directory is bind-mounted into FUXA at `/usr/src/app/FUXA/server/_project`.
It is **deliberately empty of project files** on a fresh clone.

FUXA has no headless project import. The mimic and the alarm surface are built
through the browser at `http://localhost:1881` and FUXA writes its project back
into this directory, which is what puts it under version control.

**Build it in this order — the order matters:**

1. **Device first.** Settings → Devices → add an OPC UA client:
   `opc.tcp://gateway:4840/mined/conv001/`, username `engineer`, password
   `eng1neer-demo`. Use the container hostname `gateway`, not `localhost` —
   FUXA runs inside the compose network, and `localhost` there is FUXA itself.
2. **Tags second.** Browse the address space to
   `Enterprise → PilbaraSite → ProcessingArea → ConveyingCell → CONV001`
   and select the seven measurements plus the two commands.
3. **Mimic third.** Nothing on the screen may be drawn before the tag it
   displays exists. A mimic built first acquires placeholder tags that never
   get replaced, and every HMI that shows a number nobody can trace started
   that way.

## Why `engineer` and not `historian`

FUXA needs to write `StartCommand` and `StopCommand`. The `historian` account
cannot write any node — that is the whole point of having two accounts
(see `plant/gateway/opcua_server.py`).

This is also the first place in the programme where a real question appears:
**the HMI holds a credential that can start the conveyor.** It is correct for
the demo and it is the finding that ZCR 5 risk R-14 describes. Recording it
here rather than fixing it is deliberate — S8 needs something to attack.
