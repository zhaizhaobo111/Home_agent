"""测试 LangGraph API 调用 — 确保 langgraph dev 已在端口 2024 启动."""

import httpx
import json

BASE = "http://localhost:2024"


def test_api():
    with httpx.Client(timeout=30) as client:
        # 1. 健康检查
        print("1. 健康检查...")
        r = client.get(f"{BASE}/ok")
        print(f"   状态: {r.status_code} {r.text}")

        # 2. 创建 thread
        print("\n2. 创建 thread...")
        r = client.post(f"{BASE}/threads", json={})
        thread = r.json()
        thread_id = thread["thread_id"]
        print(f"   thread_id: {thread_id}")

        # 3. 发送消息（流式）
        print("\n3. 发送消息: '帮我推荐北京 3000-5000 的房子'")
        r = client.post(
            f"{BASE}/threads/{thread_id}/runs/stream",
            json={
                "assistant_id": "house_agent",
                "input": {
                    "messages": [
                        {"role": "user", "content": "帮我推荐北京 3000-5000 的房子"}
                    ]
                },
                "config": {
                    "configurable": {"user_id": "test_user_001"}
                },
            },
        )
        print(f"   状态: {r.status_code}")

        # 解析 SSE 流
        print("\n4. 解析 SSE 流...")
        current_event = None
        for line in r.text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    if current_event == "__interrupt__":
                        print(f"\n   ⚡ 中断事件!")
                        if isinstance(data, list) and data:
                            print(f"   提示: {data[0].get('value', '')[:200]}")
                        elif isinstance(data, dict):
                            print(f"   提示: {data.get('value', '')[:200]}")
                    elif current_event == "values":
                        msgs = data.get("messages", [])
                        if msgs:
                            last = msgs[-1]
                            content = last.get("content", "")
                            msg_type = last.get("type", last.get("role", ""))
                            if content and msg_type in ("ai", "human"):
                                print(f"\n   📝 [{msg_type}] {content[:300]}")
                    elif current_event == "metadata":
                        print(f"   📋 metadata: run_id={data.get('run_id', 'N/A')}")
                except json.JSONDecodeError:
                    pass

        print("\n✅ 测试完成!")


if __name__ == "__main__":
    test_api()
