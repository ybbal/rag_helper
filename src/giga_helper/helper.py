import logging
import time

from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.memory import ConversationBufferMemory

from giga_helper import VERBOSE
from giga_helper.rag import RAG
from giga_helper.settings import GigaSettings

logging.basicConfig()
if VERBOSE:
    logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)
    logging.getLogger("langchain_community.chat_models.gigachat").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

_logger = logging.getLogger(__name__)


class GigaHelper:
    def __init__(self, llm, emdeddings, memory=None):
        self.memory = memory or ConversationBufferMemory(memory_key="history", input_key="question", output_key="text")
        self.rag: RetrievalQA = RAG(llm, emdeddings, self.memory).chain

    def get_answer(self, question):
        chain_invoke = self.rag.invoke({"question": question, "history": self.memory.buffer_as_str})
        return chain_invoke.get("text")

    async def aget_answer(self, question):
        chain_invoke = await self.rag.ainvoke({"question": question, "history": self.memory.buffer_as_str})
        return chain_invoke.get("text")


if __name__ == '__main__':
    settings = GigaSettings(stand="ext")
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    while True:
        user_input = input("Вопрос: ")
        start = time.time()
        answer = giga.get_answer(user_input)
        print(f"Время ответа: {time.time() - start} сек.")
        print(f"Ответ: {answer}")
        # print("Начало исходного документа: ", res.get("source_documents"))
        # print(qa_chain.combine_documents_chain.memory)
        print()
