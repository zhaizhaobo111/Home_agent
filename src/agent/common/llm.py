import os

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi
load_dotenv(override=True)

model = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0
)
