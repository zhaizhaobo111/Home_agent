
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from src.agent.common.context import ContextSchema
from src.agent.state.recommend import RecommendState


def collect_user_info(state:RecommendState,runtime:Runtime[ContextSchema],*,store:BaseStore):
    """收集用户希望的推荐信息"""
    #1.获取需要被解析的数据，获取最新的用户消息+用户的偏好数据