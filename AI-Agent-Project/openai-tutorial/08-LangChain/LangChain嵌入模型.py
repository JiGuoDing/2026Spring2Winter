from langchain_community.embeddings import DashScopeEmbeddings

# 不传递 model 参数，默认用的是 text-embedding-v1 模型
embed_model = DashScopeEmbeddings()

# 不用 invoke, stream
# 调用 embed_query, embed_documents
print(embed_model.embed_query("hello world"))
print(embed_model.embed_documents(["hello world", "fuck you world"]))