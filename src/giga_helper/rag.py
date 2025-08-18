import os
from typing import Optional

from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate, ChatPromptTemplate
from langchain_core.vectorstores import VectorStoreRetriever

from giga_helper import VERBOSE
from giga_helper.documents_db import get_vector_db


class RAG:
    _retriever: Optional[VectorStoreRetriever] = None

    def __init__(self, llm, emdeddings, memory=None):
        self.memory = memory or ConversationBufferMemory(memory_key="history", input_key="question", output_key="text")
        self.chain: RetrievalQA = RetrievalQA.from_chain_type(
            llm, retriever=RAG.get_retriever(emdeddings)
            , chain_type="stuff"
            # Should be one of "stuff", "map_reduce", # "map_rerank", and "refine". ,
            , return_source_documents=True
            , verbose=VERBOSE
            , input_key="question"
            , output_key="text"
            , chain_type_kwargs={"verbose": VERBOSE,
                                 "prompt": RAG.get_prompt(),
                                 "memory": self.memory,
                                 "output_key": "text",
                                 }
        )

    @classmethod
    def get_retriever(cls, emdeddings):
        if not cls._retriever:
            cls._retriever = get_vector_db(emdeddings).as_retriever(
                search_type="similarity",
                # Can be "similarity" (default), "mmr", or "similarity_score_threshold"
                search_kwargs={"k": 2})
        return cls._retriever

    @staticmethod
    def get_prompt():
        system_prompt_template = f"""{os.getenv("FINAL_PROMPT_START")}
----------------
При подготовке ответа клиенту используй следующую информацию, как основополагающую.
{{context}}
----------------
Текущий разговор:
{{history}}"""

        messages = [
            SystemMessagePromptTemplate.from_template(system_prompt_template),
            HumanMessagePromptTemplate.from_template("{question}"),
        ]
        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt
