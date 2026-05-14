from typing import Optional

from pydantic import BaseModel, Field

class ReservedInfo(BaseModel):
    """预定信息"""
    order_id:str=Field(description="预定id")
    title:str=Field(description="预定房源标题")
    phone_number:str=Field(description="预定手机号")
    price:Optional[str]=Field(
        default=None,
        description="预定的房源价格。单位：元/月"
    )
    introduction:Optional[str]=Field(
        default=None,
        description="预定房源介绍"
    )
    city_name:Optional[str]=Field(
        default=None,
        description="预定的房源所在城市"
    )
    region:Optional[str]=Field(
        default=None,
        description="预定的房源所在地区"
    )

class UserPreferences(BaseModel):
    """用户偏好数据"""
    budget_min:Optional[float]=Field(
        default=None,
        description="用户的最低预算。单位：元/月"
    )
    """用户偏好数据"""
    budget_max:Optional[float]=Field(
        default=None,
        description="用户的最高预算。单位：元/月"
    )
    reserved_info:Optional[list[ReservedInfo]]=Field(
        default=None,
        description="预约的房源列表"
    )