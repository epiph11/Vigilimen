"""Container health check: open a real, authenticated OPC UA session.

A listener that accepts a TCP connection and answers nothing is the failure
this stack is meant to make visible, so this logs in and disconnects.
Exit 0 = healthy, 1 = not. Lives in a file, not in the Dockerfile: an inline
`python -c` collapses to one line, and `async def` cannot follow a `;`.
"""
import asyncio
import sys

from asyncua import Client

URL = "opc.tcp://127.0.0.1:4840/vigilimen/conv001/"


async def check() -> None:
    c = Client(URL, timeout=4)
    c.set_user("historian")
    c.set_password("h1st0r1an-demo")
    await c.connect()
    await c.disconnect()


try:
    asyncio.run(check())
except Exception as exc:                 # any failure = unhealthy
    print(f"healthcheck failed: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
