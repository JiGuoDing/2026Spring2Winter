"""并发端口扫描器。

这个示例会先启动一个本地 TCP 服务端，再用线程池扫描几个相邻端口，
用来演示“短连接探测 + 超时 + 有界并发”的基本思路。
"""

from __future__ import annotations

import queue
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_listener(port_queue: queue.Queue[int], stop_event: threading.Event) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.2)
        port_queue.put(listener.getsockname()[1])

        while not stop_event.is_set():
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            with connection:
                pass


def probe_port(host: str, port: int, timeout: float = 0.5) -> tuple[int, str, float]:
    started_at = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            status = "open"
    except OSError:
        status = "closed"
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return port, status, elapsed_ms


def main() -> None:
    port_queue: queue.Queue[int] = queue.Queue(maxsize=1)
    stop_event = threading.Event()
    server_thread = threading.Thread(target=run_listener, args=(port_queue, stop_event), daemon=True)
    server_thread.start()

    open_port = port_queue.get(timeout=3)
    candidate_ports = sorted({port for port in [open_port, open_port + 1, open_port + 2] if 0 < port <= 65535})

    results: list[tuple[int, str, float]] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(probe_port, "127.0.0.1", port, 0.5) for port in candidate_ports]
        for future in as_completed(futures):
            results.append(future.result())

    for port, status, elapsed_ms in sorted(results):
        print(f"127.0.0.1:{port} -> {status} ({elapsed_ms:.2f} ms)")

    stop_event.set()
    server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
