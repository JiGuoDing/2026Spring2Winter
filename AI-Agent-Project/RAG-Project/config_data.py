md5_path = "./md5.text"

# Chroma
collection_name = "rag"
persist_directory = "./chroma_db"

# spliter
chunk_size = 1000
chunk_overlap = 100
separators = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
# 分割的阈值，小于该阈值的不分割
min_split_char_number = 1000

# 相似度检索
# 检索返回匹配的向量数量阈值
similarity_threshold = 2


