from typing import TypedDict, Optional
from langgraph.graph import MessagesState

# 主图状态
class State(MessagesState):
    user_preferences: dict
    user_intent:str
    # 预定流程字段
    title: Optional[str] = None
    phone_number: Optional[str] = None
    id_card: Optional[str] = None
    reserve: Optional[str] = None
    cancel: Optional[bool] = None
# 私有状态
class NeedReserveOotPut(TypedDict):
    reserve:str # 需要、不需要
