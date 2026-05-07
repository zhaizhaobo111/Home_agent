# 推荐房源状态
from langgraph.graph import MessagesState


class RecommendState(MessagesState):
    # 用户偏好(数据共享)
    user_preferences: dict
    # 以下是推荐的关键参数
    city: str # 城市
    budget_min: float # 最低预算
    budget_max: float # 最⾼预算
    district: str # 区域
    room_type: str # 房屋类型
    orientation: str # 朝向
    room_count: int # 推荐数量
    others: str # 其它要求