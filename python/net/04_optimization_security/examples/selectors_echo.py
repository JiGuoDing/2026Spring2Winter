"""使用 selectors 模块实现的事件驱动回显服务。"""

from __future__ import annotations

import queue
import selectors
import socket
import threading
import types


def accept_connection(listener: socket.socket, selector: selectors.BaseSelector) -> None:
    connection, address = listener.accept()
    print(f"server accepted: {address}")
    connection.setblocking(False)
    data = types.SimpleNamespace(address=address, outb=bytearray())
    selector.register(connection, selectors.EVENT_READ, data=data)


def service_connection(key: selectors.SelectorKey, mask: int, selector: selectors.BaseSelector) -> None:
    connection = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:
        received = connection.recv(1024)
        if received:
            data.outb.extend(received.upper())
            selector.modify(connection, selectors.EVENT_WRITE, data=data)
        else:
            selector.unregister(connection)
            connection.close()
            return

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = connection.send(data.outb)
            del data.outb[:sent]
        if not data.outb:
            selector.modify(connection, selectors.EVENT_READ, data=data)


def run_server(port_queue: queue.Queue[int], stop_event: threading.Event) -> None:
    selector = selectors.DefaultSelector()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.setblocking(False)
        selector.register(listener, selectors.EVENT_READ, data=None)
        port_queue.put(listener.getsockname()[1])

        try:
            while not stop_event.is_set():
                events = selector.select(timeout=0.2)
                for key, mask in events:
                    if key.data is None:
                        accept_connection(key.fileobj, selector)
                    else:
                        service_connection(key, mask, selector)
        finally:
            selector.close()


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
    clients = [threading.Thread(target=run_client, args=(name, port)) for name in ["alpha", "beta", "gamma"]]
    for client in clients:
        client.start()
    for client in clients:
        client.join()

    stop_event.set()
    server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
