import os
import json
from typing import Sequence
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

# * message_to_dict：单个消息对象 (BaseMessage 类实例) -> 字典
# * messages_from_dict：字典列表 -> 消息对象列表

class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id, storage_dir):
        super().__init__()
        # 会话 id
        self.session_id = session_id
        # 不同会话的历史的存储文件所在的目录路径
        self.storage_dir = storage_dir
        # 完整的会话历史文件路径
        self.file_path = os.path.join(self.storage_dir, f"{self.session_id}.json")
        # 确保目录是存在的
        os.makedirs(self.storage_dir, exist_ok=True)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        """
        添加消息到会话历史中

        Sequence 是一个抽象基类 (Abstract Base Class, ABC), 表示有序、可索引、可迭代的序列。
        """
        all_messages = list(self.messages)
        all_messages.extend(messages)

        # 将数据同步写入本地文件中
        # 类对象写入文件 -> 二进制表示
        # 为了方便，可以将 BaseMessage 消息转为字典 (借助 json 模块以 json 字符串写入文件)
        # new_messages = []
        # for message in all_messages:
        #     d_msg = message_to_dict(message)
        #     new_messages.append(d_msg)

        new_messages = [message_to_dict(message) for message in all_messages]

        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(new_messages, f, ensure_ascii=False, indent=4)

    # @property 装饰器将 messages 方法变成成员属性用
    @property
    def messages(self) -> list[BaseMessage]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                messages_dict = json.load(f)
                return messages_from_dict(messages_dict)
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)





model = ChatTongyi(model="qwen3-max")

# prompt = PromptTemplate.from_template(
#     "你需要根据会话历史回应用户问题，对话历史: {chat_history}，用户提问: {input}，请回答"
# )

prompt = ChatPromptTemplate.from_messages([
    ("system", "你需要根据会话历史回应用户问题，对话历史："),
    MessagesPlaceholder("chat_history"),
    ("human", "请回答如下问题：{input}"),
])

str_parser = StrOutputParser()

def print_prompt(full_prompt):
    print("="*20, full_prompt.to_string(), "="*20)
    return full_prompt

base_chain = prompt | print_prompt | model | str_parser

# * 实现通过会话 id 获取 InMemoryChatMessageHistory 类对象
def get_history(session_id):
    return FileChatMessageHistory(session_id, "./chat_history")

# * 创建一个新的链，对原有链增强功能：自动附加历史消息
conversion_chain = RunnableWithMessageHistory(
    base_chain, # 被增强的原有 chain
    get_history, # 通过会话 id 获取 InMemoryChatMessageHistory 类对象
    input_messages_key = "input", # 用户输入消息在模板中的占位符
    history_messages_key = "chat_history", # 会话历史消息在模板中的占位符
)

if __name__ == "__main__":
    session_config = {
        "configurable": {
            "session_id": "user_007"
        }
    }
    # res = conversion_chain.invoke({"input": "小明有两只猫，分别叫小猫和大猫。"}, session_config)
    # print("第一次执行结果:", res)
    # res = conversion_chain.invoke({"input": "小刚有三条狗。"}, session_config)
    # print("第二次执行结果:", res)
    res = conversion_chain.invoke({"input": "总共有几个宠物？"}, session_config)
    print("第三次执行结果:", res)

