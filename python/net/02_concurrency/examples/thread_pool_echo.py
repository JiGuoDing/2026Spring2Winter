"""使用 ThreadPoolExecutor 限制并发数的 TCP 回显示例。"""

from __future__ import annotations

import queue
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def handle_client(connection: socket.socket, address: tuple[str, int]) -> None:
    with connection:
        payload = connection.recv(1024)
        if not payload:
            return
        time.sleep(0.4)
        worker_name = threading.current_thread().name
        response = f"{worker_name}:{address[1]}:{payload.decode('utf-8').strip().upper()}\n".encode("utf-8")
        connection.sendall(response)


def run_server(port_queue: queue.Queue[int], stop_event: threading.Event) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.2)
        port_queue.put(listener.getsockname()[1])

        with ThreadPoolExecutor(max_workers=2) as executor:
            while not stop_event.is_set():
                try:
                    connection, address = listener.accept()
                except socket.timeout:
                    continue
                executor.submit(handle_client, connection, address)


def run_client(name: str, port: int) -> None:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
        connection.sendall(f"{name}\n".encode("utf-8"))
        reply = connection.recv(1024).decode("utf-8").strip()
        print(f"client {name} recv: {reply}")


def main() -> None:
    port_queue: queue.Queue[int] = queue.Queue(maxsize=1)
    stop_event = threading.Event()
    server_thread = threading.Thread(target=run_server, args=(port_queue, stop_event), daemon=True)
    server_thread.start()

    port = port_queue.get(timeout=3)
    clients = [threading.Thread(target=run_client, args=(name, port)) for name in ["alpha", "beta", "gamma", "delta"]]
    for client in clients:
        client.start()
    for client in clients:
        client.join()

    stop_event.set()
    server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
