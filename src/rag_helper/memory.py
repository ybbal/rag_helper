from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import START
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from rag_helper.models import State


def add_memory_to_chain(chain: Runnable, memory: BaseCheckpointSaver) -> CompiledStateGraph:
    workflow = StateGraph(state_schema=State)

    def call_and_save(state: State):
        response = chain.invoke(state)
        # Update message history with response:
        return {"messages": [response]}

    workflow.add_edge(START, "call_and_save")
    workflow.add_node("call_and_save", call_and_save)

    return workflow.compile(checkpointer=memory)

