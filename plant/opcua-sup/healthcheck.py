"""opcua-sup health check: open a session, and require a GOOD value from the mirror.

Healthy means the supervisory server is up AND it is receiving the gateway through
fw-cell. A server that answers with Bad data is not healthy for a reader.
Exit 0 = healthy, 1 = not.
"""
import asyncio
import sys

import uasec
from asyncua import ua

URL = "opc.tcp://127.0.0.1:4840/vigilimen/conv001/"
NS = "urn:vigilimen:plant:conv001"
PATH = ("Enterprise", "PilbaraSite", "ProcessingArea", "ConveyingCell", "CONV001")


async def check() -> None:
    c = await uasec.make_client(URL, "opcua-sup-local", "opcua-sup", "historian", "h1st0r1an-demo", timeout=4)
    await c.connect()
    try:
        ns = await c.get_namespace_index(NS)
        n = c.nodes.objects
        for p in PATH:
            n = await n.get_child(f"{ns}:{p}")
        dv = await (await n.get_child(f"{ns}:Running")).read_data_value(raise_on_bad_status=False)
        if not dv.StatusCode.is_good():
            raise RuntimeError(f"mirror status {dv.StatusCode}")
    finally:
        await c.disconnect()


try:
    asyncio.run(check())
except Exception as exc:
    print(f"healthcheck failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
