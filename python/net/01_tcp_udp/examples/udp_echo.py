"""UDP 收发示例。

这个示例展示了 UDP 的 sendto / recvfrom 用法，以及它与 TCP 的一个重要差异：
UDP 天然保留消息边界，一次 recvfrom 通常对应一次 sendto。
"""

from __future__ import annotations

import socket
import threading


def run_server(server_socket: socket.socket) -> None:
    server_socket.settimeout(0.5)
    while True:
        try:
            data, client_address = server_socket.recvfrom(4096)
        except socket.timeout:
            continue

        if data == b"quit":
            print("server received quit signal")
            break

        print(f"server received from {client_address}: {data!r}")
        server_socket.sendto(data.upper(), client_address)


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        server_port = server_socket.getsockname()[1]

        server_thread = threading.Thread(target=run_server, args=(server_socket,), daemon=True)
        server_thread.start()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
            client_socket.settimeout(3)
            server_address = ("127.0.0.1", server_port)

            message = b"hello udp"
            print(f"client send: {message!r}")
            client_socket.sendto(message, server_address)
            data, _ = client_socket.recvfrom(4096)
            print(f"client recv: {data!r}")

            client_socket.sendto(b"quit", server_address)

        server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
