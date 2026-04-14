from langchain_core.vectorstores import InMemoryVectorStore
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import CSVLoader

# vector_store = InMemoryVectorStore(
#     embedding=DashScopeEmbeddings()
# )

vector_store = Chroma(
    # 当前向量存储库的命名，类似数据库的表名称
    collection_name="test",
    # 嵌入模型
    embedding_function=DashScopeEmbeddings(),
    # 指定向量数据存放的目录
    persist_directory="./chroma_db",
)

loader = CSVLoader(
    file_path="./data/info.csv",
    encoding="utf-8",
    source_column="source",
)

documents = loader.load()

# vector_store.add_documents(
#     # 被添加的文档，类型为 list[Document]
#     documents=documents,
#     # 给添加的文档提供 id (字符串)，类型为 list[str]
#     ids=[f"id_{i}" for i in range(len(documents))]
# )

# 删除 传入[id, id...]
# vector_store.delete(["id_0", "id_1"])

# 检索
result = vector_store.similarity_search(
    query="which coding language is the best?",
    k=3,
    filter={"source": "sgg"},
)

print(result)