"""FastAPI 代理服务器 — serve 前端页面 + 转发请求到 LangGraph Server."""

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

LANGGRAPH_URL = "http://localhost:2024"


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("frontend/index.html", encoding="utf-8") as f:
        return f.read()


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{LANGGRAPH_URL}/{path}"
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    # SSE 流式转发
    if "stream" in path:
        client = httpx.AsyncClient(timeout=None)
        req = client.build_request(request.method, url, content=body, headers=headers)
        resp = await client.send(req, stream=True)

        async def stream():
            async for chunk in resp.aiter_bytes():
                yield chunk
            await resp.aclose()
            await client.aclose()

        return StreamingResponse(
            stream(),
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "text/event-stream"),
        )

    # 普通请求转发
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            request.method, url, content=body, headers=headers
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
