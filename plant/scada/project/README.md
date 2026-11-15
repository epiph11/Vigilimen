# FUXA project directory

This directory is bind-mounted into FUXA at `/usr/src/app/FUXA/server/_project`.
It is **deliberately empty of project files** on a fresh clone.

FUXA has no headless project import. The mimic and the alarm surface are built
through the browser at `http://localhost:1881` and FUXA writes its project back
into this directory, which is what puts it under version control.

> **Since ADR-023 (accepted 15 Nov 2026) the project has TWO OPC UA devices, not one.**
> `python3 plant/scada/project/build_project.py` generates both; import the JSON (FUXA editor,
> gear, Project, Import: it REPLACES the whole project). Then set the credentials by hand:
> read device `opc.tcp://opcua-sup:4840/vigilimen/conv001/` as `scada` / `sc4da-demo`;
> command device `opc.tcp://fw-cell:4840/vigilimen/conv001/` as `engineer` / `eng1neer-demo`.
> The steps below describe the manual build and use the old single device; read them with that in mind.

**Build it in this order — the order matters:**

1. **Device first.** Settings → Devices → add an OPC UA client:
   `opc.tcp://gateway:4840/vigilimen/conv001/`, username `engineer`, password
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

FUXA needs to write `StartCommand` and `StopCommand`. On the gateway the two
accounts differ in attribution, not in authorisation (ADR-017): `historian` can
write them too. ADR-023 therefore moves everything that only reads to `opcua-sup`,
which has no command node at all; the command device (`engineer`) is the only
writer path.

This is also the first place in the programme where a real question appears:
**the HMI holds a credential that can start the conveyor.** It is correct for
the demo and it is the finding that ZCR 5 risk R-14 describes. Recording it
here rather than fixing it is deliberate — S8 needs something to attack.
