"""
LLM Agent — 使用 OpenAI 兼容大模型驱动对话和工具调用

架构：
  1. ChatOpenAI 作为推理引擎
  2. 5 个工具函数供 LLM 调用（搜索、相册 CRUD、统计）
  3. Agent 循环：理解意图 → 调用工具 → 生成自然语言回复
"""

import json
import uuid
import logging
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.crud import photo as photo_crud
from app.crud import album as album_crud
from app.services.search_service import (
    clip_search_by_text,
)

logger = logging.getLogger("app.services.agent.llm")

# ── 系统提示词 ──────────────────────────────────────

SYSTEM_PROMPT = """你是一个 AI 智能相册助手，能帮用户管理和回忆他们的照片。

你可以：
- 搜索照片（按关键词、时间、地点、人物）
- 创建和管理相册
- 查看照片统计数据
- 帮用户回忆和讲述照片中的故事

回复要求：
- 用中文交流，语气温暖自然
- 涉及照片时，描述你找到的内容并给出数量
- 创建相册成功后，告诉用户相册名称和添加了多少张照片
- 如果用户想要的功能你做不到，诚实告知并建议替代方案
- 回复简洁、有条理，适当使用 emoji"""


# ── LLM 初始化 ──────────────────────────────────────

_llm: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    """获取或创建 ChatOpenAI 实例"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
            temperature=0.7,
        )
    return _llm


# ── 工具定义 ────────────────────────────────────────

# 这些工具函数的 docstring 会被 LLM 读取，所以要用自然语言描述参数


@tool
def search_photos(
    keyword: str = "",
    person_name: Optional[str] = None,
    top_k: int = 20,
) -> dict:
    """搜索照片。当用户想找特定内容、人物、场景的照片时调用。
    
    Args:
        keyword: 搜索关键词，如"海边"、"日落"、"猫咪"
        person_name: 人物名字，如"妈妈"、"小明"。不需要则留空
        top_k: 返回照片数量，默认20
    """
    pass  # 实际实现在 _execute_tool 中


@tool
def create_album_tool(
    name: str,
    description: str = "",
) -> dict:
    """创建新相册。当用户想整理照片、创建合集时调用。
    
    Args:
        name: 相册名称
        description: 相册描述（可选）
    """
    pass


@tool
def add_to_album(
    album_id: str,
    photo_ids: List[str],
) -> dict:
    """把照片添加到已有相册。需要知道 album_id（从最近创建的相册或相册列表中获取）。
    
    Args:
        album_id: 相册ID
        photo_ids: 要添加的照片ID列表
    """
    pass


@tool
def list_albums() -> dict:
    """列出当前用户的所有相册。当用户问'我有哪些相册'时调用。"""
    pass


@tool
def get_stats() -> dict:
    """获取照片统计信息。当用户问'我有多少照片'、'占了多少空间'时调用。"""
    pass


# 工具注册表
TOOLS = [search_photos, create_album_tool, add_to_album, list_albums, get_stats]

# 工具名称 → 函数映射
TOOL_MAP = {
    "search_photos": search_photos,
    "create_album_tool": create_album_tool,
    "add_to_album": add_to_album,
    "list_albums": list_albums,
    "get_stats": get_stats,
}


# ── 工具执行 ────────────────────────────────────────


def _execute_tool(tool_name: str, tool_args: dict, db: Session, owner_id: str) -> str:
    """执行工具调用，返回 JSON 字符串结果"""
    try:
        if tool_name == "search_photos":
            keyword = tool_args.get("keyword", "")
            person_name = tool_args.get("person_name")
            top_k = tool_args.get("top_k", 20)

            if not keyword and not person_name:
                keyword = "照片"  # 无边搜索回退

            results = clip_search_by_text(
                db=db,
                query_text=keyword,
                top_k=min(top_k, 50),
                owner_id=owner_id,
            )

            # 如果有人名过滤
            if person_name and results:
                from app.services.search_service import search_faces_by_name
                face_ids = set(search_faces_by_name(db, person_name, owner_id))
                if face_ids:
                    results = [r for r in results if r["photo_id"] in face_ids]

            return json.dumps({
                "found": len(results),
                "photos": [
                    {"id": r["photo_id"], "score": round(r.get("score", 0), 3)}
                    for r in results[:top_k]
                ],
            }, ensure_ascii=False)

        elif tool_name == "create_album_tool":
            name = tool_args.get("name", "未命名相册")
            description = tool_args.get("description", "")
            album = album_crud.create_album(
                db=db,
                owner_id=uuid.UUID(owner_id),
                name=name,
                description=description or None,
            )
            return json.dumps({
                "success": True,
                "album_id": str(album.id),
                "name": name,
            }, ensure_ascii=False)

        elif tool_name == "add_to_album":
            album_id = tool_args.get("album_id", "")
            photo_ids = tool_args.get("photo_ids", [])
            added = 0
            for pid in photo_ids:
                if album_crud.add_photo_to_album(db, uuid.UUID(album_id), uuid.UUID(pid)):
                    added += 1
            return json.dumps({
                "success": True,
                "added": added,
                "total": len(photo_ids),
            }, ensure_ascii=False)

        elif tool_name == "list_albums":
            albums = album_crud.get_user_albums(db, uuid.UUID(owner_id))
            return json.dumps({
                "albums": [
                    {"id": str(a.id), "name": a.name, "photo_count": album_crud.get_album_photo_count(db, a.id)}
                    for a in albums
                ]
            }, ensure_ascii=False)

        elif tool_name == "get_stats":
            count = photo_crud.get_user_photo_count(db, uuid.UUID(owner_id))
            storage = photo_crud.get_storage_used(db, uuid.UUID(owner_id))
            return json.dumps({
                "total_photos": count,
                "storage_mb": round(storage / 1024 / 1024, 1) if storage else 0,
            }, ensure_ascii=False)

        else:
            return json.dumps({"error": f"未知工具: {tool_name}"})

    except Exception as e:
        logger.error(f"工具执行失败 [{tool_name}]: {e}")
        return json.dumps({"error": str(e)})


# ── Agent 主循环 ────────────────────────────────────


def run_llm_agent(
    user_message: str,
    db: Session,
    owner_id: str,
    session_id: str,
    history: Optional[List[dict]] = None,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """
    执行 LLM Agent 对话

    Args:
        user_message: 用户输入文本
        db: 数据库会话
        owner_id: 用户 UUID
        session_id: 会话 UUID
        history: 历史消息列表 [{"role": "user"|"assistant", "content": str}, ...]
        image_bytes: 可选的上传图片

    Returns:
        {"reply": str, "results": list, "total": int, "tool_calls": list}
    """
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    # 构建消息列表
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # 添加历史消息（最多保留最近 10 轮）
    if history:
        for msg in history[-20:]:  # 最多 20 条历史消息
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

    # 添加当前用户消息
    user_content = user_message
    if image_bytes:
        user_content = f"[用户上传了一张图片] {user_message}" if user_message else "[用户上传了一张图片，请帮我分析]"
    messages.append(HumanMessage(content=user_content))

    # 第一轮：LLM 决定是否调用工具
    response = llm_with_tools.invoke(messages)

    tool_results_for_frontend = []
    all_photos = []

    # 处理工具调用（最多 3 轮）
    for _round in range(3):
        if not response.tool_calls:
            break

        tool_messages = []
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Agent 调用工具: {tool_name}({tool_args})")
            result_json = _execute_tool(tool_name, tool_args, db, owner_id)
            result_data = json.loads(result_json)

            # 收集搜索结果中的照片
            if tool_name == "search_photos" and "photos" in result_data:
                for p in result_data["photos"]:
                    all_photos.append({"photo_id": p["id"], "score": p.get("score", 0)})

            tool_results_for_frontend.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result_data,
            })

            tool_messages.append(ToolMessage(content=result_json, tool_call_id=tool_id))

        messages.append(response)
        messages.extend(tool_messages)

        # 下一轮
        response = llm_with_tools.invoke(messages)

    # LLM 最终回复
    reply = response.content if hasattr(response, 'content') else str(response)

    return {
        "reply": reply,
        "results": all_photos[:20],
        "total": len(all_photos),
        "tool_calls": tool_results_for_frontend,
    }
