from langchain_core.messages import SystemMessage
from langgraph.graph import MessagesState

from src.agent.common.llm import model


def extend_node(state:MessagesState):
    model.invoke(
        [SystemMessage(content="你是一个乐于助人的助手，可以根据历史对话进行问题的回复")]
        +state["messages"]
    )