import re
import uuid
from typing import Annotated, Any
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode, ToolRuntime, InjectedStore
from langgraph.types import interrupt
from langchain.tools import tool
from src.agent.common.llm import model
from src.agent.common.store import ReservedInfo, UserPreferences
from src.agent.state.reserve import ReserveState

_CANCEL_KEYWORDS = {"取消", "退出", "不需要", "跳过", "算了"}

def _is_cancel(text: str) -> bool:
    return text.strip() in _CANCEL_KEYWORDS

def get_title(state: ReserveState):
    prompt = '请输⼊要预定的房源名称（输⼊"取消"可退出）'
    while True:
        title = interrupt(prompt)
        if _is_cancel(title):
            return {"cancel": True}
        if not title or not title.strip():
            prompt = "房源名称不能为空，请重新输⼊。"
        else:
            return {"title": title.strip()}

def get_phone(state: ReserveState):
    prompt = '请输⼊要预定的⼿机号（输⼊"取消"可退出）'
    while True:
        phone_number = interrupt(prompt)
        if _is_cancel(phone_number):
            return {"cancel": True}
        if not phone_number or not phone_number.strip():
            prompt = "⼿机号不能为空，请重新输⼊。"
        elif not re.match(r"^1[3-9]\d{9}$", phone_number.strip()):
            prompt = f"'{phone_number}' 不是有效的⼿机号，请输⼊11位⼿机号码。"
        else:
            return {"phone_number": phone_number.strip()}

def get_id(state: ReserveState):
    prompt = '请输⼊要预定的⾝份证号码（输⼊"取消"可退出）'
    while True:
        id_card = interrupt(prompt)
        if _is_cancel(id_card):
            return {"cancel": True}
        if not id_card or not id_card.strip():
            prompt = "⾝份证号码不能为空，请重新输⼊。"
        elif not re.match(r"^\d{17}[\dXx]$", id_card.strip()):
            prompt = f"'{id_card}' 不是有效的⾝份证号码，请输⼊18位⾝份证号码。"
        else:
            return {"id_card": id_card.strip()}
# 节点：新增预定消息
def add_reserve_message(state: ReserveState):
    reserve_prompt = """根据提供的信息，帮我预定房源。
    - 预定的房源标题: {title}
    - ⽤⼾预定号码: {phone_number}
    - ⽤⼾⾝份证号码: {id_card}"""
    reserve_message = HumanMessage(content=reserve_prompt.format(
    title=state['title'],
    phone_number=state['phone_number'],
    id_card=state['id_card']
    ))
    return {
        "messages":[reserve_message]
    }
# 工具节点：1.生成工单 2.持久化存储
# 运行时数据 ： ToolRuntime
# store:Annotated[Any,InjectedStore()] 在工具中注入才能使用store 固定搭配
@tool
def generate_orders(phone_number:str,id_card:str,title:str,
                    runtime:ToolRuntime,store:Annotated[Any,InjectedStore()])->str:
    """
    根据⽤⼾电话，⾝份证，预定房源。
Args:
    phone_number: ⽤⼾电话
    id_card: ⾝份证
    title: ⽤⼾要预定的房源标题
    runtime: ⼯具的运⾏时信息
    store: 注⼊⼯具的持久存储
    """
    # 持久化存储到mysql
    # 1.生成工单号
    order_id=str(uuid.uuid4())
    # 2.构建预定信息
    reserved_info=ReservedInfo(
        order_id=order_id,
        phone_number=phone_number,
        title=title,
    )
    # 3. 持久化存储
    user_id = runtime.context.get("user_id") if runtime.context else None
    if not user_id:
        return f"预定失败：无法获取用户信息"
    namespace=(user_id,"preferences")
    # 查询
    prefs_result=store.search(namespace)
    if len(prefs_result)==0:
        # 无持久化信息 新增
        prefs=UserPreferences(
            reserved_info=[reserved_info]
        )
        store.put(
            namespace,
            str(uuid.uuid4()),
            prefs.model_dump(exclude_none=True)
        )
    else:
        # 有偏好数据更新
        prefs=prefs_result[0].value or {}
        prefs.setdefault("reserved_info",[]).append(reserved_info.model_dump())
        store.put(
            namespace,
            prefs_result[0].key,
            prefs
        )
    return f"已预定房源为：{title}，预定工单号为：{order_id}"

def cancel_node(state: ReserveState):
    return {"messages": [AIMessage(content="已取消预定，如需帮助请随时告诉我~")]}

def _should_continue(state: ReserveState):
    return "cancel" if state.get("cancel") else "continue"

tool_node=ToolNode([generate_orders])
# 节点： 执行模型：1.决定执行工具2.返回最终结果
def call_orders(state: ReserveState):
    result=model.bind_tools([generate_orders]).invoke(
        [SystemMessage(content="你是⼀个⼯单⽣成的助⼿，⽀持调⽤⼯具进⾏房源预定⼯单⽣成。⽀持查看查询的结果并返回最终答案")]
        +state["messages"]
    )
    return {
        "messages":[result]
    }