import os
import uuid

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage, BaseMessage
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
        agent_mode: bool = False,
) -> CompiledStateGraph:
    vector_store = load_or_get_vector_store(embeddings)

    @tool(response_format="content_and_artifact")
    def retrieve(query: str):
        """Получить информацию для ответа."""
        retrieved_docs = vector_store.similarity_search(query, k=2)
        serialized = "\n\n".join(
            doc.page_content
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    def force_retrieve(state: State):
        def transform_human_content(content):
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                return "\n".join(
                    message.get("text")
                    for message in content
                    if message.get("type") == "text"
                )
            return ""

        rag_query = "\n".join(
            transform_human_content(message.content)
            for message in state["messages"]
            if message.type == "human"
        )
        rag_content = retrieve.invoke(rag_query)
        return {"messages": ToolMessage(content=rag_content, tool_call_id=uuid.uuid4())}

    # Step 1: Generate an AIMessage that may include a tool-call to be sent.
    def query_or_respond(state: State):
        """Generate tool call for retrieval or respond."""
        llm_with_tools = llm.bind_tools([retrieve])
        system_message_content = os.getenv("FINAL_PROMPT_START")
        prompt = [SystemMessage(system_message_content)] + state["messages"]
        response = llm_with_tools.invoke(prompt)
        # MessagesState appends messages to state instead of overwriting
        return {"messages": [response]}

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

        async def add_attachment_if_exists(prompt: list[BaseMessage], state: State) -> list[BaseMessage]:
            if state.get("attachment") and isinstance(llm, GigaChat):
                with open(state["attachment"], "rb") as file_reader:
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

        # Run
        prompt = await add_attachment_if_exists(prompt, state)
        response = llm.invoke(prompt)
        return {"messages": [response]}

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
