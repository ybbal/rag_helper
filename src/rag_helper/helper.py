import logging
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from rag_helper.llms import ModelsStorage
from rag_helper.models import State
from rag_helper.rag import get_rag_chain

_logger = logging.getLogger(__name__)


class RagHelper:
    def __init__(self, llm, embeddings, memory: BaseCheckpointSaver | None = None):
        self.rag_chain = get_rag_chain(llm=llm, embeddings=embeddings, memory=memory or MemorySaver())

    def get_answer(self, question: str | None, attachment: Path | None = None):
        inputs: State = State(
            messages=[HumanMessage(content=question or "")],
            attachment= attachment,
        )
        # if attachment:
        #     inputs["attachments"] = [attachment.read()]
        chain_invoke = self.rag_chain.invoke(
            input=inputs,
            config=RunnableConfig(configurable={"thread_id": "thread_id"}),
        )
        return chain_invoke["messages"][-1].content

    async def aget_answer(self, question: str | None, attachment: Path | None = None):
        inputs: State = State(
            messages=[HumanMessage(content=question or "")],
            attachment= attachment,
        )
        # if attachment:
        #     inputs["attachments"] = [attachment.read()]
        chain_invoke = await self.rag_chain.ainvoke(
            input=inputs,
            config=RunnableConfig(configurable={"thread_id": "thread_id"}),
        )
        return chain_invoke["messages"][-1].content


if __name__ == '__main__':
    models_storage = ModelsStorage(stand="ext")
    helper = RagHelper(models_storage.chat_model, models_storage.embeddings)
    while True:
        user_input = input("Вопрос: ")
        start = time.time()
        answer = helper.get_answer(user_input)
        print(f"Время ответа: {time.time() - start} сек.")
        print(f"Ответ: {answer}")
        # print("Начало исходного документа: ", res.get("source_documents"))
        # print(qa_chain.combine_documents_chain.memory)
        print()
