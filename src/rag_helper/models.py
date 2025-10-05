from dataclasses import dataclass
from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    input_attachment_path: str | None
    output_attachment_paths: list[str] | None
    need_feedback: bool


@dataclass
class RagHelperAnswer:
    text_message: str
    attachment_paths: list[str] | None = None
    need_feedback: bool = False
