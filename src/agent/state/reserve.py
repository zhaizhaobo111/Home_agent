from langgraph.graph import MessagesState


class ReserveState(MessagesState):
    title: str  # 预定的房源
    phone_number: str  # 预定电话
    id_card: str  # ⾝份证


