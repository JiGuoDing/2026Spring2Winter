import os
import hashlib

from utils.logger_handler import logger
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader


def get_file_md5_hex(file_path: str):
    """
    获取文件的 md5 十六进制字符串
    :return:
    """

    if not os.path.exists(file_path):
        logger.error(f"[md5 计算] 文件 {file_path} 不存在")
        return

    if not os.path.isfile(file_path):
        logger.error(f"[md5 计算] {file_path} 不是一个文件")
        return

    md5_obj = hashlib.md5()
    # 4 KB 分片，避免文件过大爆内存
    chunk_size = 4096
    try:
        # * 要计算 md5 值就必须以二进制读取文件
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
            md5_hex = md5_obj.hexdigest()
            return md5_hex
    except Exception as e:
        logger.error(f"计算文件 {file_path} md5 失败，{str(e)}")
        return None

def listdir_with_allowed_suffix(dir_path: str, allowed_suffixes: tuple[str]):
    """
    返回目录下的指定后缀的文件列表
    :return:
    """
    files = []
    if not os.path.isdir(dir_path):
        logger.error(f"[listdir_with_allowed_suffix] {dir_path} 不是一个目录")
        return allowed_suffixes

    for f in os.listdir(dir_path):
        if f.endswith(allowed_suffixes):
            files.append(os.path.join(dir_path, f))

    return tuple(files)

def pdf_loader(file_path: str, passwd=None) -> list[Document]:
    """
    pdf 文件加载器
    :return:
    """

    return PyPDFLoader(file_path=file_path, password=passwd).load()

def txt_loader(file_path: str) -> list[Document]:
    """
    文本文件加载器
    :return:
    """

    return TextLoader(file_path=file_path).load()