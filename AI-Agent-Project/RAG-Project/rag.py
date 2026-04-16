from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda

from vector_stores import VectorStoreService

from file_history_store import get_history

from loguru import logger

import config_data as config


class RAGService(object):
    def __init__(self):
        self.vector_service = VectorStoreService(
            embedding=DashScopeEmbeddings(
                model=config.embedding_model
            )
        )
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "以我提供的参考资料为主，简洁而专业地回答用户问题。参考资料：{context}。"),
                ("system", "并且我提供用户的对话历史，如下所示："),
                MessagesPlaceholder("history"),
                ("user", "请回答用户提问：{input}"),
            ]
        )
        self.chat_model = ChatTongyi(model=config.chat_model)
        self.str_output_parser = StrOutputParser()
        self.chain = self.__get_chain()

    def __format_document(self, docs: list[Document]) -> str:
        if not docs:
            return "无相关参考资料。"
        formatted_str = ""
        for doc in docs:
            formatted_str += f"相关文档片段：{doc.page_content}\n文档元数据：{doc.metadata}\n\n"
        return formatted_str

    def __print_prompt(self, prompt):
        logger.info("=" * 20)
        logger.info(prompt.to_string())
        logger.info("=" * 20)
        return prompt

    def __extract_for_retriever(self, value: dict) -> str:
        return value["input"]

    def __extract_for_prompt_template(self, value: dict) -> dict:
        new_value = {"input": value["input"]["input"], "context": value["context"],
                     "history": value["input"]["history"]}
        return new_value

    def __get_chain(self):
        """获取最终执行链"""
        retriever = self.vector_service.get_retriever()

        chain = (
                {
                "input": RunnablePassthrough(),
                "context": RunnableLambda(self.__extract_for_retriever) | retriever | self.__format_document
            } | RunnableLambda(self.__extract_for_prompt_template) | self.prompt_template | self.__print_prompt | self.chat_model | self.str_output_parser
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )

        return conversation_chain

if __name__ == "__main__":
    # session id 配置
    session_config = {
        "configurable": {
            "session_id": "user_007",
        }
    }
    res = RAGService().chain.invoke(input={"input": "一个有效的合同的标准是怎样的？"}, config=session_config)
    logger.info(res)