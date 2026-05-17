"""使用 gRPC 运行一个最小的问候服务。

这个脚本会在运行时调用 grpc_tools.protoc，根据 hello.proto 生成临时 Python stub，
然后在本地启动服务端并发起一次客户端调用。
"""

from __future__ import annotations

import importlib
import sys
import tempfile
from concurrent import futures
from pathlib import Path


def generate_stubs(proto_path: Path, output_dir: Path) -> None:
    try:
        from grpc_tools import protoc
    except ImportError as exc:  # pragma: no cover - 运行时提示
        raise RuntimeError("请先安装 grpcio 和 grpcio-tools：pip install grpcio grpcio-tools") from exc

    arguments = [
        "protoc",
        f"-I{proto_path.parent}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        str(proto_path),
    ]
    if protoc.main(arguments) != 0:
        raise RuntimeError("proto 代码生成失败")


def main() -> None:
    try:
        import grpc
    except ImportError:  # pragma: no cover - 运行时提示
        print("请先安装 grpcio：pip install grpcio grpcio-tools")
        return

    proto_path = Path(__file__).with_name("hello.proto")
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        try:
            generate_stubs(proto_path, temp_dir)
        except RuntimeError as exc:
            print(exc)
            return
        sys.path.insert(0, temp_dir_name)
        try:
            hello_pb2 = importlib.import_module("hello_pb2")
            hello_pb2_grpc = importlib.import_module("hello_pb2_grpc")

            class GreeterService(hello_pb2_grpc.GreeterServicer):
                def SayHello(self, request, context):
                    return hello_pb2.HelloReply(message=f"Hello, {request.name}!")

            server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
            hello_pb2_grpc.add_GreeterServicer_to_server(GreeterService(), server)
            port = server.add_insecure_port("127.0.0.1:0")
            server.start()

            channel = grpc.insecure_channel(f"127.0.0.1:{port}")
            grpc.channel_ready_future(channel).result(timeout=3)
            stub = hello_pb2_grpc.GreeterStub(channel)
            response = stub.SayHello(hello_pb2.HelloRequest(name="Python"))
            print(response.message)

            server.stop(0).wait()
        finally:
            sys.path.remove(temp_dir_name)


if __name__ == "__main__":
    main()
