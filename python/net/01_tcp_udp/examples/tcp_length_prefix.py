"""TCP 长度前缀协议示例。

这个示例会在本机启动一个 TCP 服务端，然后用客户端发送三条消息。
消息使用 4 字节大端长度前缀封包，便于展示粘包与拆包的处理方式。
"""

from __future__ import annotations

import queue
import socket
import struct
import threading
from typing import Optional


FRAME_HEADER = struct.Struct("!I")


def send_frame(connection: socket.socket, payload: bytes) -> None:
    frame = FRAME_HEADER.pack(len(payload)) + payload
    connection.sendall(frame)


def recv_exact(connection: socket.socket, size: int) -> Optional[bytes]:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            return None
        chunks.extend(chunk)
    return bytes(chunks)


def recv_frame(connection: socket.socket) -> Optional[bytes]:
    header = recv_exact(connection, FRAME_HEADER.size)
    if header is None:
        return None

    (payload_size,) = FRAME_HEADER.unpack(header)
    return recv_exact(connection, payload_size)


def handle_client(connection: socket.socket) -> None:
    with connection:
        connection.settimeout(3)
        while True:
            payload = recv_frame(connection)
            if payload is None:
                break
            print(f"server received: {payload!r}")
            send_frame(connection, payload.upper())


def run_server(port_queue: queue.Queue[int]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port_queue.put(listener.getsockname()[1])

        connection, address = listener.accept()
        print(f"server accepted: {address}")
        handle_client(connection)


def run_client(port: int) -> None:
    messages = [b"hello", b"length-prefix", b"python socket"]
    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
        for message in messages:
            print(f"client send: {message!r}")
            send_frame(connection, message)

        # 告诉服务端已经没有更多待发送数据了，方便服务端优雅退出循环。
        connection.shutdown(socket.SHUT_WR)

        for _ in messages:
            reply = recv_frame(connection)
            if reply is None:
                break
            print(f"client recv: {reply!r}")


def main() -> None:
    port_queue: queue.Queue[int] = queue.Queue(maxsize=1)
    server_thread = threading.Thread(target=run_server, args=(port_queue,), daemon=True)
    server_thread.start()

    port = port_queue.get(timeout=3)
    run_client(port)
    server_thread.join(timeout=3)


if __name__ == "__main__":
    main()
