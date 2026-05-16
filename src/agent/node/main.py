from langchain_core.messages import SystemMessage, filter_messages, HumanMessage
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from typing_extensions import Literal

from src.agent.common.context import ContextSchema
from src.agent.common.llm import model
from src.agent.state.main import State, NeedReserveOotPut


# 节点：查询持久化信息
def get_store_info(state:State,runtime:Runtime[ContextSchema],*,store:BaseStore):
    # 搜索用户消息
    # user_id=runtime.context.get("user_id")
    user_id = runtime.context.get("user_id") if runtime.context else None
    if not user_id:
        return {"user_preferences": {}}
    namespace=(user_id,"preferences")
    prefs_result=store.search(namespace)
    if prefs_result and prefs_result[0]:
        return{
            "user_preferences":prefs_result[0].value
        }
    else:
        return {
            "user_preferences":{}
        }
class UserIntendMessage(BaseModel):
    type:Literal["recommend_house","reserve_house","get_info","others"]=Field(
        description="根据用户问题描述，判断问题类型：推荐房源、预定房源、获取信息、其他内容"
    )
# 节点：识别用户意图
def identify_question(state:State):
    # 用户问题-》LLM-》结构化输出（type）：推荐、预定、我的、其他
    prompt="""
    你是一个根据描述提取信息的专家，请从用户的描述中提取想要咨询的相关信息。
    严谨的根据语义推断信息、但是不能猜测或者编造信息
    """
    user_intent=model.with_structured_output(UserIntendMessage).invoke(
        [SystemMessage(content=prompt)]
        +[state["messages"][-1]]
    )
    return {
        "user_intent":user_intent.type if user_intent else "others"
    }

# 节点：中断询问是否需要帮助预定房源
def need_reserve(state:State)->NeedReserveOotPut:
    prompt=f"已经为您推荐合适的房源，是否需要帮您预定房源？\n"
    prompt+="如果不需要，请输入'**不需要**'\n"
    prompt+="如果需要，请输入'**需要**'\n(注意输入其他无效)\n"
    answer=interrupt(prompt)
    return {
        "reserve":answer
    }
# 节点：返回用户偏好信息
def get_user_preferences(state:State):
    # 最新的历史偏好信息
    prefs=state.get("user_preferences",{})
    # 筛选用户信息,获取到用户问题
    user_messages=filter_messages(state["messages"],include_types="human")
    reserved_info=prefs.get("reserved_info",[])
    reserved_str = "\n"
    if reserved_info:
        for i,item in enumerate(reserved_info,1):
            reserved_str+=f"{i}. 预定⼯单ID: {item.order_id}, " \
                            f"房源标题: {item.title}, " \
                            f"预定电话: {item.phone_number}\n"
    response=model.invoke(
        [SystemMessage(content="""你是⼀个乐于助⼈的助⼿，可以根据⽤⼾偏好信息进⾏回复。
如果有的偏好数据为空，不要猜测或编造数据。
不要直接回复偏好数据是什么，要结合问题进⾏⽣动回复。
如果问题与⽤⼾偏好数据⽆关，直接回复即可。"""
                       ),
        HumanMessage(content="⽤⼾的历史偏好信息如下："
f"1. 最低预算：{prefs.get('budget_min')}"
f"2. 最⾼预算：{prefs.get('budget_max')}"
f"3. 已预定过的信息：{reserved_str}")]
        +[user_messages[-1]]
    )
    return {
        "messages":[response]
    }
