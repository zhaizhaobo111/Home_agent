from langchain.chat_models import init_chat_model

model=init_chat_model("qwen-turbo",model_provider="openai",temperature=0)