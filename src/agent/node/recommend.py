import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import filter_messages, HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.types import interrupt
from pydantic import BaseModel
from pydantic import Field

from src.agent.common.context import ContextSchema
from src.agent.common.llm import model
from src.agent.common.store import UserPreferences
from src.agent.state.recommend import RecommendState, get_recommend_info


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
        description="用户的最低预算，单位为元/月，如果是xx以内，要设置最小值为0"
    )
    budget_max: Optional[float] = Field(
        default=None,
        description="用户的最⾼预算，单位为元/月，如果是xx以上，最大值设为10000"
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
    # filter_messages 过滤函数
    # 用户信息
    user_messages=filter_messages(state["messages"],include_types="human")
    # 用户偏好信息
    pref=state.get("user_preferences")
    if pref and (pref.get("budget_min") is not None or pref.get("budget_max") is not None):
        extract_messages=[
            HumanMessage(content="用户的历史偏好信息如下："
                                 f"1.最低预算：{pref["budget_min"]}"
                                 f"2.最高预算：{pref["budget_max"]}"),
                         user_messages[-1]
        ]
    else:
        extract_messages=[user_messages[-1]]

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
    # 询问用户查询城市


    # 检查是否缺失关键信息
    missing_info=[]
    # 城市为空，添加城市
    if not updated_state.get("city"):
        missing_info.append("**城市**")
    if updated_state.get("budget_min")is None or updated_state.get("budget_max")is None:
        missing_info.append("**预算范围**")
    if missing_info:
        prompt = f"为了给您推荐合适的房源，还需要您补充以下需求信息：{', '.join(missing_info)}。\n"
        prompt += "例如：'北京 预算3000-5000'，或者输入'**跳过**'，我会使用默认条件为您推荐。"
        # 根据缺失的信息进行中断
        answer=interrupt(prompt)
        if str(answer).strip() in ("跳过", "不提供"):
        #已经缺失关键信息，而且用户还不提供，需要给关键信息设置默认值
            if not updated_state.get("city"):
                updated_state["city"]="随机城市"
            if not updated_state.get("budget_min"):
                updated_state["budget_min"]=500.0
            if not updated_state.get("budget_max"):
                updated_state["budget_max"]=5000.0
            if not updated_state.get("room_count"):
                updated_state["room_count"]=5
        else:
        # 缺失关键信息，用户已补充
        # 将answer构建为HumanMessage
            user_response_message=HumanMessage(content=str(answer))
            # 提取到的信息
            extracted=extract_info([user_response_message])
            # 将提取到的信息更新到update_state里面
            # updated_state包含了中断的结果
            updated_state=update_state(updated_state,extracted)
            # 补充默认值，确保流程继续
            if not updated_state.get("city"):
                updated_state["city"]="随机城市"
            if updated_state.get("budget_min") is None:
                updated_state["budget_min"]=500.0
            if updated_state.get("budget_max") is None:
                updated_state["budget_max"]=5000.0
            if not updated_state.get("room_count"):
                updated_state["room_count"]=5

    # 4.持久化处理：更新预算
    # 最新的用户消息：北京 3套 预算：0-5000元
    # 用户的偏好数据：预算 1000-2000
    if updated_state.get("budget_min")or updated_state.get("budget_max"):
        # 有可能会更新
        user_id = runtime.context.get("user_id") if runtime.context else None
        if not user_id:
            return updated_state
        namespace=(user_id,"preferences")
        # 通过namespaces拿到store里的 用户偏好数据

        pre_result=store.search(namespace)

        # 新增或更新操作
        if len(pre_result)==0:
            # pre_result没内容-》新增
            prefs = UserPreferences(
                budget_min=updated_state.get('budget_min'),
                budget_max=updated_state.get('budget_max'),
            )
            store.put(
                # namespace key value
                namespace,
                str(uuid.uuid4()),
                prefs.model_dump(exclude_none=True)
            )
            updated_state["user_preferences"]=prefs.model_dump(exclude_none=True)
        else:
            # 有持久化信息。判断更新
            # store: 1000-5000
            # state: 2000 -3000 不用更新
            #state : 500-6000  需要更新 store：500-6000
            # 拿到value
            prefs=pre_result[0].value
            store_min=prefs.get("budget_min")
            store_max=prefs.get("budget_max")
            cur_min=updated_state.get("budget_min")
            cur_max=updated_state.get("budget_max")
            update_min=False
            update_max=False
            # 判断是否更新
            if store_min is not None and cur_min is not None and cur_min<store_min:
                # 都不为空，比较
                update_min=True
            elif  store_min is None and cur_min is not None:
                update_min=True


            if store_max is not None and cur_max is not None and cur_max>store_max:
                update_max=True
            elif store_max is None  and cur_max is not None:
                update_max=True


            if update_min or update_max:
                if update_min:
                    prefs["budget_min"] = cur_min
                if update_max:
                    prefs["budget_max"] = cur_max

            store.put(
                namespace,
                pre_result[0].key,
                prefs
            )
    # 5. 准备最终的消息，并更新
    updated_state["messages"]=[HumanMessage(content=get_recommend_info(updated_state))]
    print(f"已收集⽤⼾信息: 城市={updated_state.get('city')}, "
          f"区域={updated_state.get('district')}, "
          f"预算={updated_state.get('budget_min')}-{updated_state.get('budget_max')}, "
          f"房间数={updated_state.get('room_count')}")

    return updated_state
#使用.env环境变量
load_dotenv()

db_user = os.getenv('DB_USER')
# print(db_user)
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_name = os.getenv('DB_NAME')
db = SQLDatabase.from_uri(f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}")

# 获取数据库⼯具
toolkit = SQLDatabaseToolkit(db=db, llm=model)
tools = toolkit.get_tools()
# print(tools)

# ⼯具节点封装
# 节点：获取表信息
get_schema_tool=next(tool for tool in tools if tool.name=="sql_db_schema")#获取表的详细信息，如表结构、⽰例数据等。
get_schema_node=ToolNode([get_schema_tool],name="get_schema")#工具执行节点
# 节点：执行sql查询
run_query_tool=next(tool for tool in tools if tool.name=="sql_db_query")#⽤来执⾏ SQL
run_query_node=ToolNode([run_query_tool],name="run_query")#工具执行节点

# QuerySQLDatabaseTool ：执⾏ SQL 查询并返回结果。
# ◦ InfoSQLDatabaseTool ：获取指定表的 schema 和⽰例数据。
# ◦ ListSQLDatabaseTool ：列出数据库中的所有表。
# ◦ QuerySQLCheckerTool ：在运⾏前检查 SQL 查询的正确性。
def list_tables(state:RecommendState):
    # 1.获取AIMessages(tool_calls): 调用llm_call
    #（手动模拟）
    tool_call={
        "name":"sql_db_list_tables",
        "args":{},
        "id":"123",
        "type":"tool_call",
    }
    # 2.手动调用工具：sql_db_list_tables
    #AIMessage(tool_call)
    # 模拟必定调用工具
    tool_call_message=AIMessage(content="",tool_calls=[tool_call])
    #ToolMessage
    list_tables_tool=next(tool for tool in tools if tool.name=="sql_db_list_tables")
    tool_message=list_tables_tool.invoke(tool_call)

    #AIMessage
    response=AIMessage(content=f"可用的的表:{tool_message.content}")
    # 3.整合结果
    # aiMessage(tool_call) toolMessage aiMessage
    return {
        "messages":[tool_call_message,tool_message,response]
    }
# 节点：绑定工具（获取表信息），让llm来必定执行工具节点,构建AIMessage（tool_call）
def call_get_schema(state:RecommendState):
    # 通过系统提示词强制要求调用工具
    system_msg = SystemMessage(content="你必须调用提供的工具来获取数据库表结构信息。不要尝试直接回答用户问题。")
    llm_with_tools=model.bind_tools([get_schema_tool])
    response=llm_with_tools.invoke([system_msg] + state["messages"])
    return {
        "messages":[response]
    }
# 构造sql
def generate_query(state:RecommendState):
    # 1. ⽤来⽣成查询 SQL 的⼯具调⽤。（⽣成第⼀个 AI message）
    # 2. ⽣成最终结果。（⽣成最后⼀个 AI message）
    generate_query_system_prompt =  """
    您是⼀个设计⽤于与SQL数据库交互的代理。
    给定⼀个输⼊问题，创建⼀个语法正确的{dialect}查询来运⾏，然后查看查询的结果并返回答案。
    需要根据rows from table的⽰例设置真实查询的值。
    除⾮⽤⼾指定了他们希望获得的特定数量的⽰例，否则始终将查询限制为最多{top_k}个结果。
    您可以按相关列对结果排序，以返回最感兴趣的结果。不要查询特定表中的所有列，只查询给定问题的
    相关列。
    不要对数据库做任何DML语句（INSERT， UPDATE， DELETE， DROP等)。
    """
    system_prompt=generate_query_system_prompt.format(
        dialect=db.dialect,
        top_k=state.get('room_count', 5) or 5
    )
    system_message=SystemMessage(content=system_prompt)
    model_with_tool=model.bind_tools([run_query_tool])
    response=model_with_tool.invoke([system_message]+state["messages"])
    return {
        "messages":[response]
    }

def check_query(state:RecommendState):
    check_query_system_prompt = """
    你是⼀个⾮常注重细节的SQL专家。仔细检查{dialect}查询中的常⻅错误，包括：
    -使⽤NULL值的NOT IN
    -在应该使⽤UNION ALL时使⽤UNION
    -使⽤BETWEEN表⽰独占范围
    -谓词中的数据类型不匹配
    -正确引⽤标识符
    -使⽤正确数量的函数参数
    -转换为正确的数据类型
    -使⽤合适的列进⾏连接
    如果存在上述任何错误，请重写查询。如果没有错误，只需复制原始查询即可。
    在运⾏此检查之后，您将调⽤适当的⼯具来执⾏查询。
    """
    prompt=check_query_system_prompt.format(
        dialect=db.dialect
    )
    system_message=SystemMessage(content=prompt)
    # ⽣成⼈工用户消息进⾏检查
    # 上⼀个节点是generate_query。如果⾛到这，必定调⽤了⼯具。这样获取到的SQL是准确的。
    # 直接把sql当作用户消息传入进行检查
    tool_call=state["messages"][-1].tool_calls[0]
    args = tool_call["args"]
    query = args.get("query") if hasattr(args, "get") else args.query
    user_message=HumanMessage(content=query)
    model_with_tool=model.bind_tools([run_query_tool])
    response=model_with_tool.invoke([system_message,user_message])
    # 目前最新的一个消息是AIMessages(tool_call)->response 可以合成一个
    response.id=state["messages"][-1].id
    return {
        "messages":[response]
    }

