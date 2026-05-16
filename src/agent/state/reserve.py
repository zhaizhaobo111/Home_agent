from typing import Optional
from langgraph.graph import MessagesState


class ReserveState(MessagesState):
    title: Optional[str] = None  # 预定的房源
    phone_number: Optional[str] = None  # 预定电话
    id_card: Optional[str] = None  # ⾝份证


