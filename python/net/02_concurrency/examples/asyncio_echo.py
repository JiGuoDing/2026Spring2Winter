"""使用 asyncio 实现的异步 IO 回显服务。"""

from __future__ import annotations

import asyncio


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peername = writer.get_extra_info("peername")
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            reply = f"{peername}:{data.decode('utf-8').strip().upper()}\n".encode("utf-8")
            writer.write(reply)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def run_client(port: int, name: str) -> str:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        writer.write(f"{name}\n".encode("utf-8"))
        await writer.drain()
        response = await reader.readline()
        return response.decode("utf-8").strip()
    finally:
        writer.close()
        await writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    async with server:
        results = await asyncio.gather(
            run_client(port, "red"),
            run_client(port, "green"),
            run_client(port, "blue"),
        )

    for item in results:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
