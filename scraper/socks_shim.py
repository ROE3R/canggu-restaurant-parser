#!/usr/bin/env python3
"""Local SOCKS5 shim: accepts unauthenticated SOCKS5 from the client, forwards
  to the authenticated upstream SOCKS5 proxy. Lets Chromium/Playwright (which
  cannot do socks5 auth) use an authenticated upstream SOCKS5 proxy.
"""
import asyncio, os, struct, sys

UP_HOST = os.environ.get("PROXY_HOST", "")
UP_PORT = int(os.environ.get("PROXY_PORT", "1080"))
USER = os.environ.get("PROXY_USER", "").encode()
PASS = os.environ.get("PROXY_PASS", "").encode()
if not UP_HOST or not USER:
    sys.exit("Set PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS env vars.")
LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 1080


async def pipe(r, w):
    try:
        while True:
            data = await r.read(65536)
            if not data:
                break
            w.write(data)
            await w.drain()
    except Exception:
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def handle(cr, cw):
    up_w = up_r = None
    try:
        # --- client greeting (no auth) ---
        hdr = await cr.readexactly(2)
        n = hdr[1]
        await cr.readexactly(n)
        cw.write(b"\x05\x00")
        await cw.drain()

        # --- client CONNECT request ---
        req = await cr.readexactly(4)
        ver, cmd, rsv, atyp = req
        if atyp == 1:
            dst = await cr.readexactly(4)
            host = ".".join(str(b) for b in dst)
        elif atyp == 3:
            ln = (await cr.readexactly(1))[0]
            host = (await cr.readexactly(ln)).decode()
        elif atyp == 4:
            dst = await cr.readexactly(16)
            host = asyncio.IPv6Address
            import ipaddress
            host = str(ipaddress.IPv6Address(dst))
        else:
            cw.close(); return
        port = struct.unpack("!H", await cr.readexactly(2))[0]

        # --- upstream authenticated handshake ---
        up_r, up_w = await asyncio.open_connection(UP_HOST, UP_PORT)
        up_w.write(b"\x05\x01\x02")
        await up_w.drain()
        resp = await up_r.readexactly(2)
        if resp != b"\x05\x02":
            cw.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00"); await cw.drain(); return
        up_w.write(b"\x01" + bytes([len(USER)]) + USER + bytes([len(PASS)]) + PASS)
        await up_w.drain()
        if (await up_r.readexactly(2))[1] != 0:
            cw.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00"); await cw.drain(); return

        # --- upstream CONNECT to the originally requested target ---
        up_w.write(b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + struct.pack("!H", port))
        await up_w.drain()
        head = await up_r.readexactly(4)
        if head[1] != 0:
            cw.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00"); await cw.drain(); return
        if head[3] == 1:
            await up_r.readexactly(4)
        elif head[3] == 3:
            ln = (await up_r.readexactly(1))[0]
            await up_r.readexactly(ln)
        elif head[3] == 4:
            await up_r.readexactly(16)
        await up_r.readexactly(2)

        cw.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await cw.drain()
        await asyncio.gather(pipe(cr, up_w), pipe(up_r, cw))
    except Exception:
        try:
            cw.close()
        except Exception:
            pass


async def main():
    srv = await asyncio.start_server(handle, "127.0.0.1", LISTEN_PORT)
    print(f"shim on 127.0.0.1:{LISTEN_PORT} -> {UP_HOST}:{UP_PORT}", flush=True)
    async with srv:
        await srv.serve_forever()


asyncio.run(main())
