"""memoryview 和 os.sendfile 的零拷贝示例。"""

from __future__ import annotations

import os
import socket
import tempfile
from pathlib import Path


def demo_memoryview() -> None:
    buffer = bytearray(b"hello network")
    view = memoryview(buffer)
    view[6:13] = b"Python!"
    print(f"memoryview result: {buffer.decode('utf-8')}")


def demo_sendfile() -> None:
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"sendfile demo payload")
        temp_path = Path(temp_file.name)

    sender = receiver = None
    try:
        sender, receiver = socket.socketpair()
        with temp_path.open("rb") as source:
            if hasattr(os, "sendfile"):
                try:
                    bytes_sent = os.sendfile(sender.fileno(), source.fileno(), 0, temp_path.stat().st_size)
                    received = receiver.recv(4096)
                    print(f"sendfile bytes={bytes_sent}, received={received!r}")
                    return
                except OSError:
                    # 某些平台虽然有 sendfile，但并不支持当前 socket 组合，直接回退即可。
                    source.seek(0)

            payload = source.read()
            sender.sendall(payload)
            received = receiver.recv(4096)
            print(f"fallback copy, received={received!r}")
    finally:
        if sender is not None:
            sender.close()
        if receiver is not None:
            receiver.close()
        temp_path.unlink(missing_ok=True)


def main() -> None:
    demo_memoryview()
    demo_sendfile()


if __name__ == "__main__":
    main()
