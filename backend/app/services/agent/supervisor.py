"""Supervisor Agent --- routes user intent to the right specialist agent.

Architecture:
    User message
        |
    Supervisor (LLM + routing prompt)
        |
    +--------+---------+---------+---------+---------+
    |        |         |         |         |         |
Search  Detection  Face   Metadata  Album   Stats
Agent   Agent      Agent  Agent     Tools    Tools

The Supervisor understands the user''s intent and delegates to the appropriate
specialist agent, then aggregates the results into a natural-language reply.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from app.config.settings import settings
from app.services.agent.detection_agent import run_detection_agent
from app.services.agent.face_agent import run_face_agent
from app.services.agent.metadata_agent import run_metadata_agent
from app.services.agent.llm_agent import (
    _execute_tool as llm_execute_tool,
    get_llm,
)
from app.services.search_service import (
    clip_search_by_text,
)

logger = logging.getLogger(__name__)


SUPERVISOR_PROMPT = """You are a supervisor agent that routes user requests to specialist agents.

CRITICAL INSTRUCTIONS:
1. You MUST call tools when the user asks for an action. Text-only replies do nothing.
2. Use Chinese keywords when user speaks Chinese. CLIP works with any language.
3. Focus on the CURRENT request. Ignore unrelated context from previous messages.
4. You have up to 8 rounds. Work STEP BY STEP across rounds.
5. For albums: search_photos FIRST, then create_album_tool + add_to_album.

1. **search_photos(keyword, person_name, objects, top_k)** --- CLIP + YOLO search.
   keyword: user''s language (Chinese if user uses Chinese)
   objects: COCO-80 English labels for YOLO filter (optional)
   Examples: keyword=植物, objects=["potted plant"]
   Chinese-to-COCO: 猫=cat 狗=dog 鸟=bird 人=person 车=car
   花/植物/盆栽=\"potted plant\"   注意: tree/flower 不是 COCO 类，请用 keyword 搜索

2. **detection_agent(target_objects, photo_ids)** --- YOLO for known photos.
3. **face_agent(action, person_name)** --- Face recognition.
4. **metadata_agent(time_range, location, camera_model)** --- Metadata search.
5. **list_albums / create_album_tool / add_to_album** --- Album management.
6. **get_stats** --- Statistics.
7. **analyze_image** --- Image analysis.

Routing rules:
- You have 8 rounds; use them to complete the full task.
- If search returns 0 results, try different keywords next round.
- Keep calling tools until the task is fully done. Do NOT stop early.
- If you say you will do it, CALL THE TOOL NOW. Do not describe plans, execute.
- After all tools are called and the task is done, summarize in Chinese.
- When result includes photo_display_names, reference them.

Semantic query patterns (use search_photos parameters to express user intent):
  "只包含车的照片" → keyword="车", objects=["car"], only=True  （简单，无须列出排除项）
  "包含车和人的照片" → keyword="车人", objects=["car","person"], match_all=True
  "有车但没人的照片" → keyword="车", objects=["car"], exclude_objects=["person"]
  "猫或狗的照片" → keyword="猫狗", objects=["cat","dog"]
  "植物的照片" → keyword="植物", objects=["potted plant"]
  "去年夏天的照片" → use metadata_agent(time_range="去年夏天") first, then search_photos
"""


@tool
def detection_agent(
    target_objects: List[str],
    photo_ids: Optional[List[str]] = None,
) -> dict:
    """YOLO object detection specialist. Check if photos contain specific physical objects.

    Args:
        target_objects: List of COCO-80 object labels to detect, e.g. ["dog", "cat", "car"]
        photo_ids: Optional list of photo IDs to check. If empty, the agent will use recent search results.
    """
    pass


@tool
def face_agent(
    action: str = "search",
    person_name: Optional[str] = None,
) -> dict:
    """Face recognition specialist. Search for people in photos.

    Args:
        action: "search" to find a person, "unnamed_list" to list unnamed faces
        person_name: The person''s name to search for (required when action="search")
    """
    pass


@tool
def metadata_agent(
    time_range: Optional[str] = None,
    location: Optional[str] = None,
    camera_model: Optional[str] = None,
) -> dict:
    """Time/location/camera metadata specialist. Search photos by metadata.

    Args:
        time_range: Natural-language time, e.g. "last summer", "2024 March"
        location: Place name, e.g. "Shanghai", "Beijing"
        camera_model: Device model, e.g. "iPhone 15"
    """
    pass


SUPERVISOR_TOOLS = [
    detection_agent,
    face_agent,
    metadata_agent,
]


def _enrich_photo_names(result: dict, db: Session) -> dict:
    """Add human-readable photo names to tool results for better LLM replies.

    Mutates the result dict in-place to add a photo_display_names list.
    """
    from app.crud import photo as photo_crud

    photo_ids: List[str] = []

    if "photo_ids" in result and isinstance(result["photo_ids"], list):
        photo_ids = result["photo_ids"]
    elif "photos" in result and isinstance(result["photos"], list):
        photo_ids = [
            p.get("photo_id") or p.get("id")
            for p in result["photos"]
            if p.get("photo_id") or p.get("id")
        ]

    if not photo_ids:
        return result

    names = []
    for pid in photo_ids:
        if len(names) >= 10:
            break
        try:
            photo = photo_crud.get_photo_by_id(db, UUID(pid))
            if photo:
                name = photo.original_name or photo.filename or pid[:8]
                names.append(name)
            else:
                names.append(pid[:8])
        except Exception:
            names.append(pid[:8])

    result["photo_display_names"] = names
    return result


def _execute_supervisor_tool(
    tool_name: str,
    tool_args: dict,
    db: Session,
    owner_id: str,
    image_bytes: Optional[bytes] = None,
    shared_photo_ids: Optional[List[str]] = None,
) -> str:
    """Execute a supervisor tool call, returning JSON string result."""
    try:
        if tool_name == "detection_agent":
            target_objects = tool_args.get("target_objects", [])
            photo_ids = tool_args.get("photo_ids") or shared_photo_ids or []

            if not target_objects:
                return json.dumps({"found": 0, "photos": [], "error": "no target_objects"}, ensure_ascii=False)

            if not photo_ids:
                keyword = " ".join(target_objects)
                clip_results = clip_search_by_text(db, keyword, top_k=100, owner_id=owner_id)
                photo_ids = [r["photo_id"] for r in clip_results]

            result = run_detection_agent(
                photo_ids=photo_ids,
                target_objects=target_objects,
                db=db,
                image_bytes=image_bytes,
            )
            _enrich_photo_names(result, db)
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "face_agent":
            action = tool_args.get("action", "search")
            person_name = tool_args.get("person_name")
            result = run_face_agent(
                person_name=person_name,
                action=action,
                db=db,
                owner_id=owner_id,
            )
            _enrich_photo_names(result, db)
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "metadata_agent":
            time_range = tool_args.get("time_range")
            location = tool_args.get("location")
            camera_model = tool_args.get("camera_model")
            result = run_metadata_agent(
                time_range=time_range,
                location=location,
                camera_model=camera_model,
                db=db,
                owner_id=owner_id,
            )
            _enrich_photo_names(result, db)
            return json.dumps(result, ensure_ascii=False)

        else:
            return llm_execute_tool(
                tool_name, tool_args, db, owner_id, image_bytes=image_bytes
            )

    except Exception as e:
        logger.error(f"Supervisor tool execution failed [{tool_name}]: {e}")
        return json.dumps({"error": str(e)})


def run_supervisor(
    user_message: str,
    db: Session,
    owner_id: str,
    session_id: str,
    history: Optional[List[dict]] = None,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """Run the Supervisor Agent to route user intent and aggregate results.

    Returns:
        {"reply": str, "results": list, "total": int, "tool_calls": list}
    """
    llm = get_llm()

    from app.services.agent.llm_agent import TOOLS as BASIC_TOOLS
    all_tools = BASIC_TOOLS + SUPERVISOR_TOOLS
    llm_with_tools = llm.bind_tools(all_tools)

    messages = [SystemMessage(content=SUPERVISOR_PROMPT)]

    if history:
        for msg in history[-20:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

    user_content = user_message
    if image_bytes:
        user_content = (f"[User uploaded an image] {user_message}"
                        if user_message else "[User uploaded an image, please analyze it]")
    messages.append(HumanMessage(content=user_content))

    response = llm_with_tools.invoke(messages)

    tool_results_for_frontend = []
    all_photos = []
    shared_photo_ids: List[str] = []

    for _round in range(8):
        if not response.tool_calls:
            break

        tool_messages = []
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Supervisor calling: {tool_name}({tool_args})")
            result_json = _execute_supervisor_tool(
                tool_name, tool_args, db, owner_id,
                image_bytes=image_bytes,
                shared_photo_ids=shared_photo_ids,
            )
            result_data = json.loads(result_json)

            # Collect results from both "photos" and "photo_ids" keys
            if "photos" in result_data:
                for p in result_data["photos"]:
                    pid = p.get("photo_id") or p.get("id")
                    if pid:
                        all_photos.append({"photo_id": pid, "score": p.get("score", 0)})
            if "photo_ids" in result_data:
                for pid in result_data["photo_ids"]:
                    all_photos.append({"photo_id": pid, "score": 0.0})
                shared_photo_ids.extend(result_data["photo_ids"])

            tool_results_for_frontend.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result_data,
            })

            tool_messages.append(ToolMessage(content=result_json, tool_call_id=tool_id))

        messages.append(response)
        messages.extend(tool_messages)
        response = llm_with_tools.invoke(messages)
        messages.append(SystemMessage(content=f"[STATE] Round {_round + 1}. Photos collected: {len(all_photos)}. IDs available: {len(shared_photo_ids)}. Tool count: {len(tool_results_for_frontend)}."))

    reply = response.content if hasattr(response, 'content') else str(response)

    seen = set()
    unique_photos = []
    for p in all_photos:
        if p["photo_id"] not in seen:
            seen.add(p["photo_id"])
            unique_photos.append(p)

    return {
        "reply": reply,
        "results": unique_photos[:20],
        "total": len(unique_photos),
        "tool_calls": tool_results_for_frontend,
    }


__all__ = [
    "run_supervisor",
    "SUPERVISOR_PROMPT",
]
