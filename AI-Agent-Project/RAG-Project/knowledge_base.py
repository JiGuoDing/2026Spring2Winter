"""
知识库脚本
"""
import datetime
import os
import hashlib
import config_data as config

from loguru import logger
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


def check_md5(md5_str: str):
    """
    检查传入的 md5 字符串是否已经被处理过了

    True 表示已经处理过，False 表示未处理过
    """
    if not os.path.exists(config.md5_path):
        # 如果文件不存在
        # 创建文件
        open(config.md5_path, 'w', encoding='utf-8').close()
        return False
    else:
        for line in open(config.md5_path, 'r', encoding='utf-8').readlines():
            line = line.strip()
            if line == md5_str:
                return True
        return False



def save_md5(md5_str: str):
    """
    将传入的 md5 字符串保存到文件内
    """
    with open(config.md5_path, 'w', encoding='utf-8') as f:
        f.write(md5_str + '\n')


def get_string_md5(input_str: str, encoding='utf-8'):
    """
    将输入的字符串转换为 md5 字符串并返回
    """
    # 将字符串转换为 bytes 字节数组
    str_bytes = input_str.encode(encoding=encoding)

    # 创建 md5 对象
    md5_obj = hashlib.md5()
    md5_obj.update(str_bytes)
    return md5_obj.hexdigest()


class KnowledgeBaseService(object):
    def __init__(self):
        # 确保持久化目录存在
        os.makedirs(config.persist_directory, exist_ok=True)
        # 向量存储的实例，Chroma 向量数据库对象
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(model="text-embedding-v4"),
            persist_directory=config.persist_directory,
        )
        # 文本分割器实例
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )

    def upload_by_str(self, data, filename):
        """
        将传入的字符串进行向量化，存入向量数据库中
        """
        md5_hex = get_string_md5(data)

        if check_md5(md5_str=md5_hex):
            return "[INFO] 内容已在知识库中"
        if len(data) > config.min_split_char_number:
            knowledge_chunks: list[str] = self.spliter.split_text(data)
        else:
            knowledge_chunks = [data]

        metadata = {
            "source": filename,
            "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "基国鼎",
        }

        self.chroma.add_texts(
            texts=knowledge_chunks,
            # 所有 chunk 共用同一份元数据
            metadatas=[metadata for _ in knowledge_chunks],
        )

        save_md5(md5_hex)

        return "[INFO] 内容已成功添加到知识库中"

if __name__ == '__main__':
    name = "基国鼎"
    r1 = get_string_md5(name)
    k_service = KnowledgeBaseService()
    res = k_service.upload_by_str(name, "test.txt")
    logger.info(res)

