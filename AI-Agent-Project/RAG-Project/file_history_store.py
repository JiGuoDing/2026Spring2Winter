import os

import json
from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict


def get_history(session_id):
    return FileChatMessageHistory(session_id=session_id, storage_dir="./chat_hisotry")

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
