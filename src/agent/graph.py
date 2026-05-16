from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing_extensions import Literal


from langgraph.prebuilt import tools_condition

from src.agent.common.context import ContextSchema
from src.agent.node.main import get_store_info, identify_question, get_user_preferences, need_reserve
from src.agent.node.extend import extend_node
from src.agent.node.reserve import get_title, get_phone, get_id, add_reserve_message, call_orders, tool_node, cancel_node, _should_continue
from src.agent.state.main import State, NeedReserveOotPut
from src.agent.recommend import recommend_graph


builder=StateGraph(State,context_schema=ContextSchema)
builder.add_node(get_store_info)
builder.add_node(identify_question)
builder.add_node("recommend_graph",recommend_graph)
builder.add_node("extend_graph",extend_node)
builder.add_node(get_user_preferences)
builder.add_node(need_reserve)
# 预定流程节点（直接节点，不用子图，确保 interrupt 事件能转发到前端）
builder.add_node(get_title)
builder.add_node(get_phone)
builder.add_node(get_id)
builder.add_node(add_reserve_message)
builder.add_node(call_orders)
builder.add_node("tool_node",tool_node)
builder.add_edge(START,"get_store_info")
builder.add_edge("get_store_info","identify_question")
# 智能路由
# "recommend_house","reserve_house","get_info","others"
def router_message(state:State)->Literal["recommend_graph","get_title",
                                "extend_graph","get_user_preferences"]:
     user_intent=state["user_intent"]
     if user_intent=="recommend_house":
         return "recommend_graph"
     elif user_intent=="reserve_house":
         return "get_title"
     elif user_intent=="get_info":
         return "get_user_preferences"
     else:
         return "extend_graph"
builder.add_conditional_edges(
    "identify_question",
    router_message,
    ["recommend_graph","get_title","extend_graph","get_user_preferences"]
)
#路由1 ：推荐子图
builder.add_edge("recommend_graph","need_reserve")
def should_reserve(state:NeedReserveOotPut):
    reserve=state["reserve"]
    if reserve=="需要":
        return "get_title"
    else:
        return END
builder.add_conditional_edges(
    "need_reserve",
    should_reserve,
    ["get_title",END]
)
# 路由2：预定流程（直接节点，每步检查取消）
builder.add_node(cancel_node)
builder.add_conditional_edges("get_title", _should_continue, {"continue": "get_phone", "cancel": "cancel_node"})
builder.add_conditional_edges("get_phone", _should_continue, {"continue": "get_id", "cancel": "cancel_node"})
builder.add_conditional_edges("get_id", _should_continue, {"continue": "add_reserve_message", "cancel": "cancel_node"})
builder.add_edge("add_reserve_message","call_orders")
builder.add_edge("cancel_node",END)
builder.add_conditional_edges(
    "call_orders",
    tools_condition,
    {"tools":"tool_node","__end__":END}
)
builder.add_edge("tool_node","call_orders")
#路由3 ：拓展子图
builder.add_edge("extend_graph",END)
#路由4 ：其他子图
builder.add_edge("get_user_preferences",END)
graph=builder.compile()
# print(graph.get_graph(xray=True).draw_mermaid())

