"""TCP reachability probe, copied into a container by prove-isolation.ps1.

    python3 tcp_probe.py <host> <port>

Prints exactly one word the caller can classify:
  CONNECTED   a TCP session opened            -> there is a route AND a listener
  REFUSED     the host answered "nothing here" -> there is a ROUTE (an RST came back)
  UNREACHABLE no route / no answer / timeout   -> the network blocks it

REFUSED matters. An isolation proof that counts "connection refused" as a pass has
proved the opposite: a refusal is a packet from the far side, which only exists if
the two networks are joined.
"""
import socket
import sys

host, port = sys.argv[1], int(sys.argv[2])
s = socket.socket()
s.settimeout(3)
try:
    s.connect((host, port))
    print("CONNECTED")
except ConnectionRefusedError:
    print("REFUSED")
except OSError as e:                       # unreachable, timed out, name not known
    print("UNREACHABLE", type(e).__name__, e)
finally:
    s.close()
