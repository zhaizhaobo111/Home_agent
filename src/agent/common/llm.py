# from langchain.chat_models import init_chat_model
#
# model=init_chat_model("qwen-turbo",model_provider="tongyi",temperature=0)
from langchain_community.chat_models import ChatTongyi

model = ChatTongyi(
    model_name="qwen-turbo",
    dashscope_api_key="sk-3b066661f42f49c9971861631950c710",  # 你的通义KEY
    temperature=0
)
# print(model.invoke("你好"))