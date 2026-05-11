from langgraph.types import interrupt


def get_title(state: ReserveState):
    prompt = "请输⼊要预定的房源名称"
    while True:
        title = interrupt(prompt)
        if title: # 可以进⾏验证
    return {"title": title}
# 每次验证失败后，提⽰信息会更新
prompt = f"'{title}' 不是⼀个有效的房源名称，请更正。"
# 节点：获取⽤⼾预定电话
def get_phone(state: ReserveState):
    prompt = "请输⼊要预定的⼿机号"
        while True:
            phone_number = interrupt(prompt)
            if phone_number: # 可以进⾏验证
                return {"phone_number": phone_number}
# 每次验证失败后，提⽰信息会更新
prompt = f"'{phone_number}' 不是⼀个有效的电话，请更正。"
# 节点：获取⽤⼾⾝份证
def get_id(state: ReserveState):
    prompt = "请输⼊要预定的⾝份证号码"
    while True:
        id_card = interrupt(prompt)
        if id_card:
            return {"id_card": id_card}
# 每次验证失败后，提⽰信息会更新
prompt = f"'{id_card}' 不是⼀个有效的⾝份证，请更正。"
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
    )