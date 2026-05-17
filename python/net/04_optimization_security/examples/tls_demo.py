"""使用 ssl.SSLContext 包装 socket 的最小 TLS 示例。

这个示例依赖系统中的 OpenSSL 命令行工具，用它生成一个临时自签名证书。
如果环境里没有 openssl，会给出提示并退出。
"""

from __future__ import annotations

import queue
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
from pathlib import Path


def generate_self_signed_cert(directory: Path) -> tuple[Path, Path]:
    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError("未找到 openssl，请先安装 OpenSSL 或跳过该示例。")

    cert_path = directory / "cert.pem"
    key_path = directory / "key.pem"
    command = [
        openssl,
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(cert_path),
        "-days",
        "1",
        "-nodes",
        "-subj",
        "/CN=localhost",
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("OpenSSL 证书生成失败，请检查系统 OpenSSL 是否可用。") from exc
    return cert_path, key_path


def run_server(port_queue: queue.Queue[int], cert_path: Path, key_path: Path) -> None:
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port_queue.put(listener.getsockname()[1])

        connection, address = listener.accept()
        print(f"server accepted: {address}")
        with server_context.wrap_socket(connection, server_side=True) as tls_connection:
            payload = tls_connection.recv(1024)
            print(f"server received: {payload!r}")
            tls_connection.sendall(payload.upper())


def run_client(port: int) -> None:
    client_context = ssl.create_default_context()
    client_context.check_hostname = False
    client_context.verify_mode = ssl.CERT_NONE

    with socket.create_connection(("127.0.0.1", port), timeout=3) as raw_socket:
        with client_context.wrap_socket(raw_socket, server_hostname="localhost") as tls_socket:
            tls_socket.sendall(b"secure hello")
            reply = tls_socket.recv(1024)
            print(f"client recv: {reply!r}")


def main() -> None:
    try:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            cert_path, key_path = generate_self_signed_cert(temp_dir)

            port_queue: queue.Queue[int] = queue.Queue(maxsize=1)
            server_thread = threading.Thread(target=run_server, args=(port_queue, cert_path, key_path), daemon=True)
            server_thread.start()

            port = port_queue.get(timeout=5)
            run_client(port)
            server_thread.join(timeout=5)
    except RuntimeError as exc:
        print(exc)


if __name__ == "__main__":
    main()
