from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing_extensions import Literal


from src.agent.common.context import ContextSchema
from src.agent.node.main import get_store_info, identify_question, get_user_preferences, need_reserve
from src.agent.state.main import State, NeedReserveOotPut
from src.agent.extend import extend_graph
from src.agent.recommend import recommend_graph
from src.agent.reserve import reserve_graph


builder=StateGraph(State,context_schema=ContextSchema)
builder.add_node(get_store_info)
builder.add_node(identify_question)
builder.add_node("recommend_graph",recommend_graph)
builder.add_node("reserve_graph",reserve_graph)
builder.add_node("extend_graph",extend_graph)
builder.add_node(get_user_preferences)
builder.add_node(need_reserve)
builder.add_edge(START,"get_store_info")
builder.add_edge("get_store_info","identify_question")
# 智能路由
# "recommend_house","reserve_house","get_info","others"
def router_message(state:State)->Literal["recommend_graph","reserve_graph",
                                "extend_graph","get_user_preferences"]:
     user_intent=state["user_intent"]
     if user_intent=="recommend_house":
         return "recommend_graph"
     elif user_intent=="reserve_house":
         return "reserve_graph"
     elif user_intent=="get_info":
         return "get_user_preferences"
     else:
         return "extend_graph"
builder.add_conditional_edges(
    "identify_question",
    router_message,
    ["recommend_graph","reserve_graph","extend_graph","get_user_preferences"]
)
#路由1 ：推荐子图
builder.add_edge("recommend_graph","need_reserve")
def should_reserve(state:NeedReserveOotPut):
    reserve=state["reserve"]
    if reserve=="需要":
        return "reserve_graph"
    else:
        return END
builder.add_conditional_edges(
    "need_reserve",
    should_reserve,
    ["reserve_graph",END]
)
#路由2 ：预定子图
builder.add_edge("reserve_graph",END)
#路由3 ：拓展子图
builder.add_edge("extend_graph",END)
#路由4 ：其他子图
builder.add_edge("get_user_preferences",END)
graph=builder.compile()
# print(graph.get_graph(xray=True).draw_mermaid())

