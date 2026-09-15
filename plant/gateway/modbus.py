#!/usr/bin/env python3
"""
Modbus TCP — a complete implementation of the parts a PLC uses.

Written from the wire format rather than pulled from a library, and that is
deliberate. The protocol is small enough to hold in one file, and holding it
in one file is what makes the central claim of the protocol register
impossible to argue with:

    MBAP header                          PDU
    ┌──────────┬──────────┬────────┬─────┬──────────────────────────┐
    │ txn id 2 │ proto  2 │ len  2 │ uid │ function code + payload  │
    └──────────┴──────────┴────────┴─────┴──────────────────────────┘

    There is nowhere in that frame to put an identity.

Not "the identity field is optional". Not "authentication is usually
disabled". There is no field. A request from the SCADA system and a request
from an adversary are byte-for-byte indistinguishable, because there is
nothing in the format that could differ.

The unit id is a bus address, not a credential — it says which device on a
serial line, not who is asking.

Function codes implemented: 1 read coils · 3 read holding registers ·
5 write single coil · 6 write single register. That is what a conveyor
needs. No dependency, so this runs anywhere Python does.
"""

from __future__ import annotations

import socket
import socketserver
import struct
import threading

FC_READ_COILS = 1
FC_READ_HOLDING = 3
FC_WRITE_COIL = 5
FC_WRITE_REGISTER = 6

ERR_ILLEGAL_FUNCTION = 0x01
ERR_ILLEGAL_ADDRESS = 0x02


class Registers:
    """Coils and holding registers, with a lock. This is the whole device."""

    def __init__(self, n_coils: int = 32, n_regs: int = 32) -> None:
        self.coils = [False] * n_coils
        self.regs = [0] * n_regs
        self.lock = threading.Lock()

    # --- convenience for the plant loop ---------------------------------
    def get_coil(self, a: int) -> bool:
        with self.lock:
            return self.coils[a]

    def set_coil(self, a: int, v: bool) -> None:
        with self.lock:
            self.coils[a] = bool(v)

    def get_reg(self, a: int) -> int:
        with self.lock:
            return self.regs[a]

    def set_reg(self, a: int, v: int) -> None:
        with self.lock:
            self.regs[a] = int(v) & 0xFFFF


def _apply(regs: Registers, pdu: bytes) -> bytes:
    """Execute one PDU and return the response PDU.

    Note what this function does NOT receive: any information about who sent
    the request. Not because it was dropped upstream — because the frame
    never carried any.
    """
    fc = pdu[0]

    try:
        if fc == FC_READ_COILS:
            addr, qty = struct.unpack(">HH", pdu[1:5])
            with regs.lock:
                bits = regs.coils[addr:addr + qty]
            if len(bits) != qty:
                return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_ADDRESS)
            nbytes = (qty + 7) // 8
            packed = bytearray(nbytes)
            for i, b in enumerate(bits):
                if b:
                    packed[i // 8] |= 1 << (i % 8)
            return struct.pack(">BB", fc, nbytes) + bytes(packed)

        if fc == FC_READ_HOLDING:
            addr, qty = struct.unpack(">HH", pdu[1:5])
            with regs.lock:
                vals = regs.regs[addr:addr + qty]
            if len(vals) != qty:
                return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_ADDRESS)
            return struct.pack(">BB", fc, qty * 2) + struct.pack(f">{qty}H", *vals)

        if fc == FC_WRITE_COIL:
            addr, val = struct.unpack(">HH", pdu[1:5])
            with regs.lock:
                if addr >= len(regs.coils):
                    return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_ADDRESS)
                # Every coil the server exposes is writable. Modbus has no
                # read-only attribute — only documentation, and documentation
                # is not a control.
                regs.coils[addr] = (val == 0xFF00)
            return pdu[:5]

        if fc == FC_WRITE_REGISTER:
            addr, val = struct.unpack(">HH", pdu[1:5])
            with regs.lock:
                if addr >= len(regs.regs):
                    return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_ADDRESS)
                regs.regs[addr] = val
            return pdu[:5]

    except (struct.error, IndexError):
        return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_ADDRESS)

    return struct.pack(">BB", fc | 0x80, ERR_ILLEGAL_FUNCTION)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        sock: socket.socket = self.request
        sock.settimeout(30)
        while True:
            try:
                head = self._recv_exact(sock, 7)
                if not head:
                    return
                txn, proto, length, uid = struct.unpack(">HHHB", head)
                pdu = self._recv_exact(sock, length - 1)
                if not pdu:
                    return
                resp = _apply(self.server.registers, pdu)  # type: ignore[attr-defined]
                sock.sendall(struct.pack(">HHHB", txn, proto, len(resp) + 1, uid) + resp)
            except (OSError, struct.error):
                return

    @staticmethod
    def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], registers: Registers) -> None:
        self.registers = registers
        super().__init__(address, _Handler)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Client:
    """A Modbus TCP client. Note the absence of a credential parameter."""

    def __init__(self, host: str = "127.0.0.1", port: int = 15020, unit: int = 1) -> None:
        self.host, self.port, self.unit = host, port, unit
        self.sock: socket.socket | None = None
        self._txn = 0

    def connect(self, timeout: float = 5.0) -> bool:
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout)
            return True
        except OSError:
            return False

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def _tx(self, pdu: bytes) -> bytes:
        assert self.sock, "not connected"
        self._txn = (self._txn + 1) & 0xFFFF
        self.sock.sendall(struct.pack(">HHHB", self._txn, 0, len(pdu) + 1, self.unit) + pdu)
        head = _Handler._recv_exact(self.sock, 7)
        if not head:
            raise ConnectionError("connection closed")
        _, _, length, _ = struct.unpack(">HHHB", head)
        resp = _Handler._recv_exact(self.sock, length - 1)
        if not resp:
            raise ConnectionError("connection closed")
        if resp[0] & 0x80:
            raise OSError(f"modbus exception {resp[1]}")
        return resp

    def read_coils(self, addr: int, count: int) -> list[bool]:
        r = self._tx(struct.pack(">BHH", FC_READ_COILS, addr, count))
        data = r[2:]
        return [(data[i // 8] >> (i % 8)) & 1 == 1 for i in range(count)]

    def read_holding(self, addr: int, count: int) -> list[int]:
        r = self._tx(struct.pack(">BHH", FC_READ_HOLDING, addr, count))
        return list(struct.unpack(f">{count}H", r[2:]))

    def write_coil(self, addr: int, value: bool) -> None:
        self._tx(struct.pack(">BHH", FC_WRITE_COIL, addr, 0xFF00 if value else 0x0000))

    def write_register(self, addr: int, value: int) -> None:
        self._tx(struct.pack(">BHH", FC_WRITE_REGISTER, addr, value & 0xFFFF))
