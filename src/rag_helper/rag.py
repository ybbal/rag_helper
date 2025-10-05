import os
import uuid

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage, BaseMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.vectorstores import VectorStore
from langchain_gigachat import GigaChat
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from rag_helper.documents_db import load_vector_store
from rag_helper.models import State


def get_rag_chain(
        llm: BaseChatModel,
        embeddings: Embeddings,
        memory: BaseCheckpointSaver | None = None,
        agent_mode: bool = True,
) -> CompiledStateGraph:
    vector_store = load_or_get_vector_store(embeddings)

    @tool(response_format="content_and_artifact")
    def retrieve(query: str):
        """Получить информацию для корректного ответа.
        Обязателен для новых вопросов, кроме обычного общения, например, привет, как дела, спасибо"""
        retrieved_docs = vector_store.similarity_search(
            query,
            k=int(os.getenv("RAG_CHUNK_COUNT")),
            # score_threshold= 150
        )
        serialized = "\n\n".join(
            doc.page_content
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    def get_retrieve_str_query(state: State) -> str:
        rag_query = "\n".join(
            transform_content_for_retrieve(message.content)
            for message in state["messages"]
            if message.type == "human" or message.type == "ai"
        )
        return rag_query

    def transform_content_for_retrieve(content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            return "\n".join(
                message.get("text")
                for message in content
                if message.get("type") == "text"
            )
        return ""

    def force_retrieve(state: State):
        rag_query = get_retrieve_str_query(state)
        rag_content_tool_message: ToolMessage = retrieve.invoke(
            {
                "name": "retrieve",
                "args": {"query": rag_query},
                "id": uuid.uuid4(),  # required
                "type": "tool_call",  # required
            }
        )
        image_paths = rag_content_tool_message.artifact[0].metadata.get('image_paths') or []
        old_image_paths = state.get("output_attachment_paths")
        return {
            "messages": rag_content_tool_message,
            "output_attachment_paths": image_paths if image_paths != old_image_paths else None
        }

    # Step 1: Generate an AIMessage that may include a tool-call to be sent.
    def query_or_respond(state: State):
        """Generate tool call for retrieval or respond."""
        llm_with_tools = llm.bind_tools([retrieve])
        system_message_content = os.getenv("FINAL_PROMPT_START")
        prompt = [SystemMessage(system_message_content)] + state["messages"]
        response: AIMessage = llm_with_tools.invoke(prompt)
        # MessagesState appends messages to state instead of overwriting
        return {
            "messages": [response],
            "need_feedback": True if response.tool_calls else False
        }

    # Step 2: Execute the retrieval.
    tools = ToolNode([retrieve])

    # Step 3: Generate a response using the retrieved content.
    async def generate(state: State):
        """Generate answer."""
        # Get generated ToolMessages
        recent_tool_messages = []
        for message in reversed(state["messages"]):
            if message.type == "tool":
                recent_tool_messages.append(message)
            else:
                break
        tool_messages = recent_tool_messages[::-1]

        # Format into prompt
        docs_content = "\n\n".join(doc.content for doc in tool_messages)
        system_message_content = (
            f"{os.getenv("FINAL_PROMPT_START")}\n"
            f"----------------\n"
            f"При подготовке ответа клиенту используй следующую информацию, как основополагающую.\n"
            f"{docs_content}\n"
            f"----------------\n"
        )
        conversation_messages = [
            message
            for message in state["messages"]
            if message.type in ("human", "system")
               or (message.type == "ai" and not message.tool_calls)
        ]
        prompt = [SystemMessage(system_message_content)] + conversation_messages

        async def add_input_attachment_if_exists(prompt: list[BaseMessage], state: State) -> list[BaseMessage]:
            if state.get("input_attachment_path") and isinstance(llm, GigaChat):
                with open(state["input_attachment_path"], "rb") as file_reader:
                    file = await llm.aupload_file(file=file_reader)
                prompt[-1].content = [
                    {
                        "type": "text",
                        "text": prompt[-1].content
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": file.id_,
                            "giga_id": file.id_
                        }
                    }
                ]
            return prompt

        prompt = await add_input_attachment_if_exists(prompt, state)
        # Run
        response = llm.invoke(prompt)

        return {
            "messages": [response],
            "output_attachment_paths": (
                tool_messages[0].artifact[0].metadata.get('image_paths')
                if tool_messages[0].artifact
                else None
            )
        }

    graph_builder = StateGraph(State)
    graph_builder.add_node(force_retrieve)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node(tools)
    graph_builder.add_node(generate)

    if agent_mode:
        graph_builder.set_entry_point("query_or_respond")
        graph_builder.add_conditional_edges(
            "query_or_respond",
            tools_condition,
            {END: END, "tools": "tools"},
        )
        graph_builder.add_edge("tools", "generate")
    else:
        graph_builder.set_entry_point("force_retrieve")
        graph_builder.add_edge("force_retrieve", "generate")

    graph_builder.add_edge("generate", END)

    return graph_builder.compile(checkpointer=memory)


_vector_store: VectorStore | None = None


def load_or_get_vector_store(embeddings: Embeddings) -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = load_vector_store(embeddings)
    return _vector_store
