"""
* 基于 streamlit 完成 Web 网页上传服务
"""
import time

# ! streamlit 当 web 页面元素发生变化，则代码重新执行一遍
import streamlit as st

from knowledge_base import KnowledgeBaseService

# 添加网页标题
st.title('知识库更新服务')

# file_uploader
uploader_file = st.file_uploader(
    label="请上传 .txt 文件",
    type=['txt'],
    # 表示仅接受一个文件的上传
    accept_multiple_files=False,
)

# session_state 就是一个字典
if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

if uploader_file is not None:
    # 提取文件的信息
    file_name = uploader_file.name
    file_type = uploader_file.type
    # 文件大小，单位为 KB
    file_size = uploader_file.size / 1024

    # 子标题，比 header 小一点
    st.subheader(f"文件名: {file_name}")
    # 在网页中写入内容
    st.write(f"格式: {file_type} | 大小: {file_size} KB")

    # getvalue -> bytes -> decode("utf-8")
    text_content = uploader_file.getvalue().decode("utf-8")

    with st.spinner("载入知识库中......"):
        time.sleep(1)
        result = st.session_state["service"].upload_by_str(text_content, file_name)

        st.write(result)