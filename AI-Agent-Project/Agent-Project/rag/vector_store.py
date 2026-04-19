import os

from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils.config_handler import chroma_config
from model.factory import embedding_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_suffix, get_file_md5_hex
from utils.logger_handler import logger

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_config["collection_name"],
            embedding_function=embedding_model,
            persist_directory=chroma_config["persist_directory"],
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_config["chunk_size"],
            chunk_overlap=chroma_config["chunk_overlap"],
            separators=chroma_config["separators"],
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_config["k"]})

    def load_document(self):
        """
        从数据目录内读取数据文件，转为向量存入向量数据库
        要计算文件的 md5 并去重
        :return: None
        """

        def check_md5_hex(md5_hex: str):
            # 转为绝对路径
            md5_hex_abs_path = get_abs_path(chroma_config["md5_hex_store"])
            if not os.path.exists(md5_hex_abs_path):
                # 尚未处理过 md5，创建文件
                open(md5_hex_abs_path, "w", encoding="utf-8").close()
                return False

            # 读取内容
            with open(md5_hex_abs_path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_hex:
                        return True
            return False

        def save_md5_hex(md5_hex: str):
            with open(get_abs_path(chroma_config["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_hex + "\n")

        def get_file_documents(read_path: str) -> list[Document]:
            if read_path.endswith(".txt"):
                return txt_loader(read_path)
            if read_path.endswith(".pdf"):
                return pdf_loader(read_path)
            return []

        allowed_files_path = listdir_with_allowed_suffix(
            dir_path=get_abs_path(chroma_config["data_path"]),
            allowed_suffixes=tuple(chroma_config["allowed_knowledge_file_suffix"]),
        )

        for path in allowed_files_path:
            # 获取文件的 md5
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex=md5_hex):
                logger.info(f"[INFO] [加载知识库] {path} 内容在知识库已存在")
                continue

            try:
                documents: list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[WARNING] [加载知识库] {path} 内未检测到有效文本")
                    continue
                splitted_documents: list[Document] = self.splitter.split_documents(documents=documents)

                if not splitted_documents:
                    logger.warning(f"[WARNING] [加载知识库] {path} 分片后没有有效文本内容")
                    continue

                self.vector_store.add_documents(documents=splitted_documents)
                save_md5_hex(md5_hex=md5_hex)
                logger.info(f"[INFO] [加载知识库] {path} 内容加载成功")
            except Exception as e:
                # exc_info = True 表示需要记录详细的报错堆栈，如果为 False 表示仅记录报错信息本身
                logger.error(f"[ERROR] [加载知识库] {path} 加载失败：{str(e)}", exc_info=True)
                continue

if __name__ == "__main__":
    vs =VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()
    res = retriever.invoke("清洗办法")
    for r in res:
        print(r.page_content)
        print("*"*20)
