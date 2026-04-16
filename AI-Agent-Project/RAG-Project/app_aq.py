import streamlit as st
import config_data as config


from rag import RAGService


def capture(generator, cache_list):
    for chunk in generator:
        cache_list.append(chunk)
        yield chunk

# 标题
st.title("Intelligent Agent")
# 分隔符
st.divider()

if "message" not in st.session_state:
    st.session_state["message"] = [{"role": "assistant", "content": "Hello, what can I do for you?"}]

# 只创建一次，避免性能问题 (否则每次刷新页面都会重新创建一个实例)
if "rag" not in st.session_state:
    st.session_state["rag"] = RAGService()

for message in st.session_state["message"]:
    st.chat_message(name=message["role"]).write(message["content"])

# 在页面最下方提供用户输入栏
prompt = st.chat_input()
if prompt:
    st.chat_message(name="user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    ai_res_list = []
    with st.spinner("Agent thinking..."):
        # time.sleep(2)
        res_stream = st.session_state["rag"].chain.stream({"input": prompt}, config.session_config)
        res = st.chat_message(name="assistant").write_stream(res_stream)
        st.session_state["message"].append({"role": "assistant", "content": res})