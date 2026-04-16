from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
import config_data as config



class VectorStoreService(object):
    def __init__(self, embedding):
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )
        
    def get_retriever(self):
        """
        获取向量检索器，方便加入
        """
        return self.vector_store.as_retriever(search_kwargs={"k": config.similarity_threshold})
        
        
if __name__ == "__main__":
    # 测试向量存储服务
    retriever = VectorStoreService(DashScopeEmbeddings(model="text-embedding-v4")).get_retriever()
    results = retriever.invoke("一个有效的合同的标准是怎样的？")
    print(results)