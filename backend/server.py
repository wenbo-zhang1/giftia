"""
Giftia - AI 情感陪伴助手（FastAPI 后端）

启动:
    uvicorn server:app --host 127.0.0.1 --port 8000 --reload
"""

import os
import sys
import uuid
import json
import asyncio
import time
import datetime
import logging
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
from collections import defaultdict, deque

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Security, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# ruff: noqa: E402
from llm_config import get_llm_client
from model_config import CHAT_MODEL, CHAT_BASE_URL, get_mem0_api_key, get_chat_api_key, detect_provider, PROVIDER_KEY_MAP
from mem0 import MemoryClient
from memory_manager import MemoryManager, Mem0Bridge
from working_memory import WorkingMemoryStore
from emotion_graph import build_emotion_graph, run_emotion_workflow_streaming, load_prompt_config, save_prompt_config, get_dialogue_prompt, DIALOGUE_AGENT_PROMPT
from file_processor import is_multimodal_model
from conversation_store import ConversationStore

# ================================================================
# 配置
# ================================================================

logger = logging.getLogger("server")

MEM0_API_KEY = ""
CHAT_API_KEY = ""
try:
    MEM0_API_KEY = get_mem0_api_key()
except ValueError:
    logger.warning("未配置 mem0_API_KEY，记忆功能不可用")
try:
    CHAT_API_KEY = get_chat_api_key()
except ValueError:
    pass
DEFAULT_USER_ID = "web_user_001"

GIFTIA_ACCESS_KEY = os.environ.get("GIFTIA_ACCESS_KEY", "")
GIFTIA_ADMIN_KEY = os.environ.get("GIFTIA_ADMIN_KEY", "")

_access_key_header = APIKeyHeader(name="X-Access-Key", auto_error=False)
_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

class MemoryLogHandler(logging.Handler):
    def __init__(self, maxlen: int = 500):
        super().__init__()
        self.buffer: deque = deque(maxlen=maxlen)
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(self.format(record))

    def get_logs(self) -> list[dict]:
        return [{"timestamp": i, "level": r.split("[")[1].split("]")[0] if "[" in r else "INFO", "message": r} for i, r in enumerate(self.buffer)]

_log_handler = MemoryLogHandler(maxlen=500)
logging.getLogger().addHandler(_log_handler)
logging.getLogger().setLevel(logging.INFO)

# ================================================================
# Metrics（可观测性）
# ================================================================

_metrics = {
    "requests_total": defaultdict(int),       # endpoint -> count
    "requests_errors": defaultdict(int),       # endpoint -> count
    "requests_duration_sum": defaultdict(float),  # endpoint -> total seconds
    "llm_calls_total": 0,
    "llm_calls_duration_sum": 0.0,
    "llm_tokens_total": 0,
    "start_time": time.time(),
}


class MetricsMiddleware(BaseHTTPMiddleware):
    """记录每个请求的耗时和状态码。"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        path = request.url.path
        # 归一化带路径参数的端点
        for prefix in ("/api/chat/", "/api/conversations/", "/api/memory/"):
            if path.startswith(prefix):
                parts = path[len(prefix):].strip("/").split("/")
                if len(parts) >= 1:
                    path = f"{prefix}{{id}}"
                break

        _metrics["requests_total"][path] += 1
        _metrics["requests_duration_sum"][path] += duration
        if response.status_code >= 400:
            _metrics["requests_errors"][path] += 1

        return response

# ================================================================
# 配置
# ================================================================

# ================================================================
# 应用生命周期
# ================================================================

_app_state: Dict[str, Any] = {}

def _validate_env_on_startup():
    provider = detect_provider()
    key_name = PROVIDER_KEY_MAP.get(provider, "API_KEY")
    if not CHAT_API_KEY:
        logger.error(f"未找到 Chat API Key。请在 .env 中设置 {key_name}=your_api_key（当前模型: {CHAT_MODEL}，提供商: {provider}）")
        sys.exit(1)

    if not MEM0_API_KEY:
        logger.warning("未配置 MEM0_API_KEY，记忆功能将降级为本地模式")
    else:
        logger.info("MEM0_API_KEY 已配置，云端记忆功能可用")

    embedding_key = os.environ.get("ZHIPU_API_KEY", "") or os.environ.get("ZhipuAI_API_KEY", "")
    if not embedding_key:
        logger.warning("未配置 Embedding API Key，语义检索将降级为关键词匹配")

    raw_origins = os.environ.get("CORS_ORIGINS", "")
    if raw_origins:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        invalid = [o for o in origins if not (o.startswith("http://") or o.startswith("https://"))]
        if invalid:
            logger.warning(f"CORS_ORIGINS 包含无效格式: {invalid}")


def _log_startup_summary():
    features = []
    features.append(f"Chat: {CHAT_MODEL} (key: {'已配置' if CHAT_API_KEY else '未配置'})")
    features.append(f"记忆: {'Mem0 云端' if MEM0_API_KEY else '仅本地'}")
    features.append(f"多模态: {'支持' if _app_state.get('multimodal') else '不支持'}")
    features.append(f"认证: {'已启用' if GIFTIA_ACCESS_KEY else '未启用'}")
    logger.info("启动配置摘要: " + " | ".join(features))

@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_env_on_startup()

    logger.info("正在初始化记忆管理器...")
    mm = MemoryManager(storage_path=os.path.join(os.path.dirname(__file__), "memory_store"))
    _app_state["memory_manager"] = mm
    _app_state["conversation_store"] = ConversationStore()
    _app_state["working_memory_store"] = WorkingMemoryStore()

    mem0_client = None
    if MEM0_API_KEY:
        try:
            mem0_client = MemoryClient(api_key=MEM0_API_KEY)
            logger.info("Mem0 客户端初始化成功")
        except Exception as e:
            logger.warning(f"Mem0 初始化失败: {e}")

    bridge = Mem0Bridge(memory_manager=mm, mem0_client=mem0_client)
    _app_state["mem0_bridge"] = bridge

    graph = build_emotion_graph(memory_manager=mm, mem0_bridge=bridge, working_memory_store=_app_state["working_memory_store"])
    _app_state["emotion_graph"] = graph

    _app_state["multimodal"] = is_multimodal_model()
    logger.info(f"多模态支持: {_app_state['multimodal']}")

    load_prompt_config()
    _log_startup_summary()
    logger.info("Giftia 后端服务已启动")
    yield
    logger.info("Giftia 后端服务已停止")

app = FastAPI(title="Giftia API", version="1.0.0", lifespan=lifespan)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# 速率限制
# ================================================================

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True

_chat_limiter = RateLimiter(max_requests=30, window_seconds=60)
_default_limiter = RateLimiter(max_requests=60, window_seconds=60)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "/api/chat" not in request.url.path:
            client_ip = request.client.host if request.client else "unknown"
            if not _default_limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试"},
                )
        response = await call_next(request)
        return response

app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)

async def rate_limit_chat(user_id: str):
    if not _chat_limiter.is_allowed(user_id):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

# ================================================================
# Pydantic 模型
# ================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="用户消息")
    conversation_id: Optional[str] = Field(None, description="当前对话 ID，不传则自动创建")
    conversation_history: List[Dict] = Field(default_factory=list, description="对话历史")
    image_data: Optional[str] = Field(None, description="图片 base64 data URL")

class ChatEvent(BaseModel):
    type: str
    text: Optional[str] = None

class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)

class PromptUpdateRequest(BaseModel):
    prompt: str = Field(..., min_length=0, max_length=5000, description="自定义对话 prompt，空字符串恢复默认")

# ================================================================
# 辅助函数
# ================================================================

async def verify_access_key(api_key: str = Security(_access_key_header)):
    if not GIFTIA_ACCESS_KEY:
        return True
    if not api_key or api_key != GIFTIA_ACCESS_KEY:
        raise HTTPException(status_code=401, detail="无效的访问密钥")
    return True

async def verify_admin_key(api_key: str = Security(_admin_key_header)):
    if not GIFTIA_ADMIN_KEY:
        if GIFTIA_ACCESS_KEY:
            if not api_key or api_key != GIFTIA_ACCESS_KEY:
                raise HTTPException(status_code=403, detail="需要管理员密钥")
        return True
    if not api_key or api_key != GIFTIA_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="需要管理员密钥")
    return True

def get_all_users() -> List[str]:
    mem_store = os.path.join(os.path.dirname(__file__), "memory_store")
    if not os.path.exists(mem_store):
        return [DEFAULT_USER_ID]
    users = []
    for filename in os.listdir(mem_store):
        if filename.endswith(".json"):
            users.append(filename[:-5])
    return sorted(users) if users else [DEFAULT_USER_ID]

def _ensure_conversation(user_id: str) -> tuple:
    store: ConversationStore = _app_state["conversation_store"]
    convs, current_id = store.load(user_id)
    if not convs:
        convs = {}
        cid = str(uuid.uuid4())
        convs[cid] = {
            "title": "新对话",
            "messages": [],
            "created": datetime.datetime.now().strftime("%m/%d %H:%M"),
        }
        current_id = cid
        store.save(user_id, convs, current_id)
    elif current_id not in convs:
        current_id = list(convs.keys())[-1]
        store.save(user_id, convs, current_id)
    return convs, current_id

# ================================================================
# API: 对话
# ================================================================

@app.post("/api/chat/{user_id}", dependencies=[Depends(verify_access_key), Depends(rate_limit_chat)])
async def chat(user_id: str, req: ChatRequest):
    if not CHAT_API_KEY:
        raise HTTPException(status_code=500, detail="未配置 LLM_API_KEY")

    user_id = user_id.strip() or DEFAULT_USER_ID

    async def event_stream():
        try:
            reply = ""
            async for chunk in run_emotion_workflow_streaming(
                memory_manager=_app_state.get("memory_manager"),
                mem0_bridge=_app_state.get("mem0_bridge"),
                user_id=user_id,
                user_message=req.message,
                conversation_history=req.conversation_history,
                image_data=req.image_data,
                working_memory_store=_app_state.get("working_memory_store"),
            ):
                chunk_type = chunk.get("type")
                if chunk_type == "status":
                    yield f"data: {json.dumps({'type': 'status', 'text': chunk.get('text', '')})}\n\n"
                elif chunk_type == "token":
                    reply += chunk.get("text", "")
                    yield f"data: {json.dumps({'type': 'token', 'text': chunk.get('text', '')})}\n\n"
                elif chunk_type == "reply":
                    reply = chunk.get("text", reply)
                    yield f"data: {json.dumps({'type': 'reply', 'text': reply})}\n\n"
                elif chunk_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'text': chunk.get('text', '')})}\n\n"
                    return

            store: ConversationStore = _app_state["conversation_store"]
            convs, current_id = _ensure_conversation(user_id)

            cid = req.conversation_id or current_id
            if cid not in convs:
                cid = str(uuid.uuid4())
                convs[cid] = {
                    "title": req.message[:20] or "新对话",
                    "messages": [],
                    "created": datetime.datetime.now().strftime("%m/%d %H:%M"),
                }

            conv = convs[cid]
            user_msg = {"role": "user", "content": req.message}
            if req.image_data:
                user_msg["image"] = req.image_data
            conv["messages"].append(user_msg)
            conv["messages"].append({"role": "assistant", "content": reply})

            if len(conv["messages"]) <= 2:
                conv["title"] = req.message[:20] or "新对话"

            store.save(user_id, convs, cid)

            yield f"data: {json.dumps({'type': 'done', 'conversation_id': cid})}\n\n"

        except Exception as e:
            logger.error(f"对话处理失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

# ================================================================
# API: 会话管理
# ================================================================

@app.get("/api/conversations/{user_id}", dependencies=[Depends(verify_access_key)])
async def get_conversations(user_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    convs, current_id = _ensure_conversation(user_id)
    items = []
    for cid, cd in convs.items():
        items.append({
            "id": cid,
            "title": cd.get("title", "新对话"),
            "created": cd.get("created", ""),
            "message_count": len(cd.get("messages", [])),
            "is_active": cid == current_id,
        })
    items.sort(key=lambda x: x["created"], reverse=True)
    return {"conversations": items, "current_id": current_id}

@app.get("/api/conversations/{user_id}/{conv_id}", dependencies=[Depends(verify_access_key)])
async def get_conversation(user_id: str, conv_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    convs, _ = _ensure_conversation(user_id)
    if conv_id not in convs:
        raise HTTPException(status_code=404, detail="对话不存在")
    return convs[conv_id]

@app.post("/api/conversations/{user_id}", dependencies=[Depends(verify_access_key)])
async def create_conversation(user_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    store: ConversationStore = _app_state["conversation_store"]
    convs, _ = _ensure_conversation(user_id)
    cid = str(uuid.uuid4())
    convs[cid] = {
        "title": "新对话",
        "messages": [],
        "created": datetime.datetime.now().strftime("%m/%d %H:%M"),
    }
    store.save(user_id, convs, cid)
    return {"id": cid, "title": "新对话", "created": convs[cid]["created"]}

@app.patch("/api/conversations/{user_id}/{conv_id}", dependencies=[Depends(verify_access_key)])
async def rename_conversation(user_id: str, conv_id: str, req: RenameRequest):
    user_id = user_id.strip() or DEFAULT_USER_ID
    store: ConversationStore = _app_state["conversation_store"]
    convs, current_id = _ensure_conversation(user_id)
    if conv_id not in convs:
        raise HTTPException(status_code=404, detail="对话不存在")
    convs[conv_id]["title"] = req.title.strip()
    store.save(user_id, convs, current_id)
    return {"ok": True, "title": req.title.strip()}

@app.delete("/api/conversations/{user_id}/{conv_id}", dependencies=[Depends(verify_access_key)])
async def delete_conversation(user_id: str, conv_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    store: ConversationStore = _app_state["conversation_store"]
    convs, current_id = _ensure_conversation(user_id)
    if conv_id not in convs:
        raise HTTPException(status_code=404, detail="对话不存在")
    del convs[conv_id]
    if not convs:
        cid = str(uuid.uuid4())
        convs[cid] = {
            "title": "新对话",
            "messages": [],
            "created": datetime.datetime.now().strftime("%m/%d %H:%M"),
        }
        current_id = cid
    elif current_id == conv_id:
        current_id = list(convs.keys())[-1]
    store.save(user_id, convs, current_id)
    return {"ok": True, "current_id": current_id}

# ================================================================
# API: 用户管理
# ================================================================

@app.get("/api/users", dependencies=[Depends(verify_access_key)])
async def get_users():
    mm: MemoryManager = _app_state["memory_manager"]
    store: ConversationStore = _app_state["conversation_store"]
    memory_users = set(mm.get_all_user_ids())
    conn = store._get_conn()
    try:
        rows = conn.execute("SELECT DISTINCT user_id FROM conversations").fetchall()
        conv_users = {r[0] for r in rows}
    except Exception:
        conv_users = set()
    all_users = sorted(memory_users | conv_users)
    if not all_users:
        all_users = [DEFAULT_USER_ID]
    result = []
    for u in all_users:
        stats = mm.get_memory_stats(u)
        result.append({
            "id": u,
            "memory_count": stats.get("total", 0),
            "consolidated_count": stats.get("consolidated_count", 0),
            "avg_importance": stats.get("avg_importance", 0),
        })
    return result

@app.post("/api/users", dependencies=[Depends(verify_access_key)])
async def create_user(user_id: str = Query(..., min_length=1, max_length=50)):
    user_id = user_id.strip()
    _ensure_conversation(user_id)
    return {"ok": True, "user_id": user_id}

# ================================================================
# API: 记忆管理
# ================================================================

@app.get("/api/memory/{user_id}/stats", dependencies=[Depends(verify_access_key)])
async def get_memory_stats(user_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    mm: MemoryManager = _app_state["memory_manager"]
    return mm.get_memory_stats(user_id)

@app.delete("/api/memory/{user_id}", dependencies=[Depends(verify_access_key)])
async def clear_memories(user_id: str):
    user_id = user_id.strip() or DEFAULT_USER_ID
    bridge: Mem0Bridge = _app_state["mem0_bridge"]
    mm: MemoryManager = _app_state["memory_manager"]
    try:
        if bridge.mem0_client:
            bridge.mem0_client.delete_all(user_id=user_id)
    except Exception as e:
        logger.warning(f"清除 Mem0 记忆失败: {e}")
    mm.delete_user_memories(user_id)
    mem_file = os.path.join(os.path.dirname(__file__), "memory_store", f"{user_id}.json")
    if os.path.exists(mem_file):
        os.remove(mem_file)
    return {"ok": True}

@app.get("/api/logs", dependencies=[Depends(verify_admin_key)])
async def get_logs(limit: int = Query(default=200, ge=1, le=500)):
    return {"logs": _log_handler.get_logs()[-limit:]}


@app.get("/api/metrics", dependencies=[Depends(verify_admin_key)])
async def get_metrics():
    """返回服务指标（Prometheus 风格）。"""
    uptime = time.time() - _metrics["start_time"]
    endpoints = []
    for path, count in _metrics["requests_total"].items():
        errors = _metrics["requests_errors"].get(path, 0)
        duration_sum = _metrics["requests_duration_sum"].get(path, 0.0)
        avg_duration = duration_sum / count if count > 0 else 0
        endpoints.append({
            "path": path,
            "requests_total": count,
            "requests_errors": errors,
            "avg_duration_ms": round(avg_duration * 1000, 1),
        })
    return {
        "uptime_seconds": round(uptime, 0),
        "endpoints": endpoints,
        "llm": {
            "calls_total": _metrics["llm_calls_total"],
            "avg_duration_ms": round(
                _metrics["llm_calls_duration_sum"] / _metrics["llm_calls_total"] * 1000, 1
            ) if _metrics["llm_calls_total"] > 0 else 0,
        },
    }

# ================================================================
# API: 配置
# ================================================================

@app.get("/api/config/model", dependencies=[Depends(verify_access_key)])
async def get_model_config():
    multimodal = _app_state.get("multimodal", False)
    return {
        "model": CHAT_MODEL,
        "base_url": CHAT_BASE_URL,
        "multimodal": multimodal,
    }

@app.get("/api/config/model-presets", dependencies=[Depends(verify_access_key)])
async def get_model_presets():
    from model_presets import PRESET_MODELS
    return PRESET_MODELS

@app.get("/api/config/prompt", dependencies=[Depends(verify_access_key)])
async def get_prompt_config():
    current = get_dialogue_prompt()
    is_custom = current != DIALOGUE_AGENT_PROMPT
    return {
        "prompt": current,
        "default_prompt": DIALOGUE_AGENT_PROMPT,
        "is_custom": is_custom,
    }

@app.put("/api/config/prompt", dependencies=[Depends(verify_admin_key)])
async def update_prompt_config(req: PromptUpdateRequest):
    save_prompt_config(req.prompt)
    current = get_dialogue_prompt()
    is_custom = current != DIALOGUE_AGENT_PROMPT
    return {
        "ok": True,
        "prompt": current,
        "is_custom": is_custom,
    }

# ================================================================
# 健康检查
# ================================================================

_health_cache: dict = {"result": None, "timestamp": 0.0}
_HEALTH_CACHE_TTL = 30


async def _check_llm_connectivity() -> str:
    if not CHAT_API_KEY:
        return "not_configured"
    try:
        client = get_llm_client(temperature=0.0, use_thinking=False)
        response = await asyncio.wait_for(
            asyncio.to_thread(client.invoke, "ping"),
            timeout=5.0,
        )
        return "ok" if response else "unreachable"
    except Exception:
        return "unreachable"


async def _check_mem0_connectivity() -> str:
    if not MEM0_API_KEY:
        return "not_configured"
    bridge: Mem0Bridge = _app_state.get("mem0_bridge")
    if not bridge or not bridge.mem0_client:
        return "unreachable"
    try:
        await asyncio.wait_for(
            asyncio.to_thread(bridge.mem0_client.search, query="ping", user_id="health_check", limit=1),
            timeout=5.0,
        )
        return "ok"
    except Exception:
        return "unreachable"


@app.get("/api/health")
async def health():
    now = time.time()
    if _health_cache["result"] is not None and (now - _health_cache["timestamp"]) < _HEALTH_CACHE_TTL:
        return _health_cache["result"]

    llm_status = await _check_llm_connectivity()
    mem0_status = await _check_mem0_connectivity()

    result = {
        "status": "ok",
        "dependencies": {
            "llm": llm_status,
            "mem0": mem0_status,
        },
        "multimodal": _app_state.get("multimodal", False),
        "auth_required": bool(GIFTIA_ACCESS_KEY),
        "admin_key_configured": bool(GIFTIA_ADMIN_KEY),
    }
    _health_cache["result"] = result
    _health_cache["timestamp"] = now
    return result


_V1_ROUTES_ADDED = False


def _add_v1_routes():
    global _V1_ROUTES_ADDED
    if _V1_ROUTES_ADDED:
        return
    _V1_ROUTES_ADDED = True
    for route in list(app.router.routes):
        if not hasattr(route, "path"):
            continue
        if not route.path.startswith("/api/"):
            continue
        if "/api/v1/" in route.path:
            continue
        v1_path = route.path.replace("/api/", "/api/v1/", 1)
        if hasattr(route, "methods") and hasattr(route, "endpoint"):
            app.add_api_route(
                v1_path,
                route.endpoint,
                methods=route.methods,
                dependencies=route.dependencies,
                response_model=route.response_model,
                tags=route.tags,
                summary=route.summary,
                description=route.description,
            )


_add_v1_routes()


if __name__ == "__main__":
    import uvicorn
    if not CHAT_API_KEY:
        provider = detect_provider()
        key_name = PROVIDER_KEY_MAP.get(provider, "API_KEY")
        logger.error("未找到 Chat API Key。请在 .env 中设置 %s=yours（当前模型: %s，提供商: %s）",
                       key_name, CHAT_MODEL, provider)
        sys.exit(1)
    logger.info("启动 Giftia API 服务...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
