from langchain_chroma import Chroma
from utils.config_handler import chroma_config
from model.factory import embedding_model

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_config["collection_name"],
            embedding_function=embedding_model,
            persist_directory=chroma_config["persist_directory"],
        )
