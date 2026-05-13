from typing import TypedDict

from langgraph.graph import MessagesState

# 主图状态
class State(MessagesState):
    user_preferences: dict
    user_intent:str
# 私有状态
class NeedReserveOotPut(TypedDict):
    reserve:str # 需要、不需要
