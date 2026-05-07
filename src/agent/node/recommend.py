from typing import Optional

from langchain_core.messages import filter_messages, HumanMessage, SystemMessage
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from onnxruntime.transformers.models.stable_diffusion.diffusion_models import BaseModel
from pydantic import Field

from src.agent.common.context import ContextSchema
from src.agent.common.llm import model
from src.agent.state.recommend import RecommendState

class UserInfo(BaseModel):
    """用户的租房需求信息"""
    city:Optional[str]=Field(
        default=None,
        description="⽤⼾所在或想要租房的城市，例如：西安、北京、上海"

    )
    district: Optional[str] = Field(
        default=None,
        description="⽤⼾想要租房的具体区域或⾏政区，例如：雁塔区、碑林区、海淀区"
    )
    budget_min: Optional[float] = Field(
        default=None,
        description="⽤⼾的最低预算，单位为元/⽉"
    )
    budget_max: Optional[float] = Field(
        default=None,
        description="⽤⼾的最⾼预算，单位为元/⽉"
    )
    room_type: Optional[str] = Field(
        default=None,
        description="房屋类型，例如：整租、合租、公寓、⼀室⼀厅、两室⼀厅"
    )
    orientation: Optional[str] = Field(
        default=None,
        description="房屋朝向，例如：朝南、朝北、东南、南北通透"
    )
    room_count: Optional[int] = Field(
        default=None,
        description="需要推荐的房屋数量"
    )
    others: Optional[str] = Field(
        default=None,
        description="特殊要求，例如：带阳台、独⽴卫⽣间、近地铁、可养宠物、有电梯等"
    )

def collect_user_info(state:RecommendState,runtime:Runtime[ContextSchema],*,store:BaseStore):
    """收集用户希望的推荐信息"""
    #1.获取需要被解析的数据，获取最新的用户消息+用户的偏好数据
    user_messages=filter_messages(state["messages"],include_types="human")
    pref=state.get("user_preferences")
    if pref and (pref["budget_min"]or pref["budget_max"]):
        extract_messages=[
            HumanMessage(content="用户的历史偏好信息如下："
                                 f"1.最低预算：{pref["budget_min"]}"
                                 f"2.最高预算：{pref["budget_max"]}"),
                         user_messages[-1]
        ]
    else:
        extract_messages=user_messages[-1]

    #2.提取信息(LLM结构化返回)
    def extract_info(messages)->UserInfo:
        system_messages=SystemMessage(
            content="""你是⼀个租房需求信息提取专家。请从⽤⼾的描述与历史信息中提取租房相关信息。
        只提取⽤⼾明确提到的信息，不要猜测或推断。
        如果某个信息⽤⼾没有提到，就返回null。
        注意预算的单位可能是元 /⽉、元 / 天等，请统⼀转换为元 /⽉。
        如果⽤⼾提到价格范围，请分别提取最低和最⾼预算。
        如果⽤⼾提到推荐⼏套房，提取room_count字段。"""
        )
        return model.with_structured_output(UserInfo).invoke(extract_messages)
    # 更新状态函数
    def update_state(current_state: dict, info: UserInfo) -> dict:
        if not info:
            return current_state

        # 获取所有⾮None的字段
        user_info_dict = info.model_dump(exclude_none=True)
        current_state.update(user_info_dict)
        return current_state
    # 根据；历史偏好和用户消息提取信息
    updated_state = {}
    extracted_info=extract_info(extract_messages)
    updated_state=update_state(updated_state,extracted_info)

    # 3.中断
    # 最新的用户消息：给我推荐房子
    #
    return updated_state