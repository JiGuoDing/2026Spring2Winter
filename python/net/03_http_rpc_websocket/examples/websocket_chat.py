"""WebSocket 广播聊天室示例。

这个脚本会在本机启动一个 WebSocket 服务端，并启动两个客户端。
两个客户端连接后，各自发送一条消息，服务端再把消息广播给所有连接。
"""

from __future__ import annotations

import asyncio


async def run_chat_demo() -> None:
    try:
        import websockets
    except ImportError:  # pragma: no cover - 运行时提示
        print("请先安装 websockets：pip install websockets")
        return

    connected_clients: set[object] = set()
    ready = asyncio.Event()
    connect_lock = asyncio.Lock()
    connected_count = 0

    async def handler(websocket) -> None:
        nonlocal connected_count
        connected_clients.add(websocket)
        async with connect_lock:
            connected_count += 1
            if connected_count >= 2:
                ready.set()
        try:
            async for message in websocket:
                await asyncio.gather(*(peer.send(message) for peer in list(connected_clients)))
        finally:
            connected_clients.discard(websocket)

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    async def client(name: str, text: str) -> list[str]:
        uri = f"ws://127.0.0.1:{port}"
        async with websockets.connect(uri) as websocket:
            await ready.wait()
            await websocket.send(f"{name}:{text}")
            received = [await websocket.recv(), await websocket.recv()]
            print(f"{name} received: {received}")
            return received

    try:
        results = await asyncio.gather(
            client("alice", "hello everyone"),
            client("bob", "hi alice"),
        )
        print(f"broadcast results: {results}")
    finally:
        server.close()
        await server.wait_closed()


def main() -> None:
    asyncio.run(run_chat_demo())


if __name__ == "__main__":
    main()
