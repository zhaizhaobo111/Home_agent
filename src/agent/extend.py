from langgraph.constants import START
from langgraph.graph import StateGraph, MessagesState

from src.agent.node.extend import extend_node

builder=StateGraph(MessagesState)
builder.add_node(extend_node)
builder.add_edge(START,"extend_node")
extend_graph=builder.compile()

