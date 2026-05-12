
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import tools_condition

from src.agent.common.context import ContextSchema
from src.agent.node.reserve import get_title, get_phone, get_id, add_reserve_message, call_orders, tool_node
from src.agent.state.reserve import ReserveState

builder=StateGraph(ReserveState,context_schema=ContextSchema)
builder.add_sequence([get_title,get_phone,get_id,add_reserve_message,call_orders])

builder.add_node("tool_node",tool_node)
builder.add_edge(
    START,"get_title")
builder.add_conditional_edges(
    "call_orders",
    tools_condition,
    {
        "tools":"tool_node",
        "__end__":END,
    }
)
builder.add_edge("tool_node","call_orders")
reserve_graph=builder.compile()
# print(reserve_graph.get_graph(xray=True).draw_mermaid())