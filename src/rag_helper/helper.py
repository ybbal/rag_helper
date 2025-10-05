import asyncio
import json
import logging
import time
from dataclasses import asdict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from rag_helper.llms import ModelsStorage
from rag_helper.models import State, RagHelperAnswer
from rag_helper.rag import get_rag_chain

_logger = logging.getLogger(__name__)

_RUNNABLE_CONFIG = RunnableConfig(configurable={"thread_id": "thread_id"})


class RagHelper:
    def __init__(self, llm, embeddings, memory: BaseCheckpointSaver | None = None):
        self.memory = memory or MemorySaver()
        self.rag_chain = get_rag_chain(llm=llm, embeddings=embeddings, memory=self.memory)

    async def aget_answer(self, question: str | None, attachment: str | None = None) -> RagHelperAnswer:
        inputs: State = State(
            messages=[HumanMessage(content=question or "")],
            input_attachment_path=attachment,
        )
        chain_invoke = await self.rag_chain.ainvoke(
            input=inputs,
            config=_RUNNABLE_CONFIG,
        )
        answer = RagHelperAnswer(
            text_message=chain_invoke["messages"][-1].content,
            attachment_paths=chain_invoke.get("output_attachment_paths")
        )
        self.rag_chain.update_state(_RUNNABLE_CONFIG, {"output_attachment_paths": None})
        return answer


async def __answer():
    user_input = input("Вопрос: ")
    start = time.time()
    answer = await helper.aget_answer(user_input)
    print(f"Время ответа: {time.time() - start} сек.")
    print(f"Ответ: {json.dumps(asdict(answer), indent=2, ensure_ascii=False)}")
    # print("Начало исходного документа: ", res.get("source_documents"))
    # print(qa_chain.combine_documents_chain.memory)
    print()


if __name__ == '__main__':
    models_storage = ModelsStorage(stand="ext")
    helper = RagHelper(models_storage.chat_model, models_storage.embeddings)
    while True:
        asyncio.run(__answer())
