"""LLM Agent --- SuperAgent V2: tools, YOLO filtering, and analyze_image

Architecture:
  1. ChatOpenAI as the reasoning engine
  2. 6 tool functions: search, albums, stats, analyze
  3. YOLO-tag filtering on search results
  4. Agent loop: intent -> tools -> natural-language response
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
from app.models.description import ImageDescription
from app.services.search_service import (
    clip_search_by_text,
)

logger = logging.getLogger("app.services.agent.llm")

# --- System Prompt ----------------------------------------------------------

SYSTEM_PROMPT = """You are an AI smart photo album assistant that helps users manage and recall their photos.

You can:
- Search photos (by keyword, time, location, person, or objects)
- Create and manage albums
- View photo statistics
- Analyze uploaded images to describe what''s inside them
- Help users recall and tell stories about their photos

Response requirements:
- Communicate in Chinese with a warm, natural tone
- When referencing photos, describe what you found and give a count
- After creating an album, tell the user the album name and how many photos were added
- If there is a feature you cannot fulfill, be honest and suggest alternatives
- Keep replies concise and well-organized, use emoji appropriately

When a user mentions specific objects (animals, vehicles, furniture, etc.):
- Pass those objects via the objects parameter to search_photos for YOLO-based verification.
- YOLO can detect 80 COCO classes including: person, dog, cat, bird, car, bicycle, motorcycle, airplane, boat, furniture, food, etc.
- If a user says "find photos with a dog and a cat", set keyword="dog cat" and objects=["dog", "cat"].
- Only use the objects parameter for concrete physical things YOLO can detect, NOT for abstract concepts like "sunset", "beach", "hiking"."""


# --- LLM singleton ----------------------------------------------------------

_llm: Optional[ChatOpenAI] = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
            temperature=0.7,
        )
    return _llm


# --- Tool definitions -------------------------------------------------------

# Docstrings are read by the LLM, so use natural-language parameter descriptions.


@tool
def search_photos(
    keyword: str = "",
    person_name: Optional[str] = None,
    objects: Optional[List[str]] = None,
    exclude_objects: Optional[List[str]] = None,
    match_all: bool = False,
    only: bool = False,
    top_k: int = 20,
) -> dict:
    """Search photos by natural-language description, object detection tags, and person names.

    Supports complex semantic queries via parameter combinations:
      - AND: keyword="车", objects=["car","person"], match_all=True  → 同时有车和人
      - OR:  keyword="宠物", objects=["cat","dog"]  → 有猫或狗
      - NOT: keyword="车", objects=["car"], exclude_objects=["person"]  → 有车但没人（只包含车）
      - ONLY: keyword="车", objects=["car"], only=True  → 只有车的照片（比 exclude_objects 更简单）

    Args:
        keyword: Search keyword in USER'S language (Chinese if user uses Chinese), e.g. "车", "动物", "海边"
        person_name: Person name, e.g. "妈妈", "小明". Leave empty if not needed.
        objects: Objects to INCLUDE (YOLO COCO-80 labels, English only), e.g. ["car", "dog", "cat"]. OR logic by default.
        exclude_objects: (不建议用于"只包含") Objects to EXCLUDE. 推荐用 only=True 代替.
        match_all: When True, ALL objects in "objects" must be present (AND logic). Default False (OR logic, any match suffices).
        top_k: Number of photos to return, default 20.

    Chinese semantic patterns (how to use the parameters):
      - "找车的照片"       → keyword="车", objects=["car"]
      - "只包含车的照片"    → keyword="车", objects=["car"], only=True
      - "包含车和人的照片"  → keyword="车人", objects=["car","person"], match_all=True
      - "有车但没人的照片"  → keyword="车", objects=["car"], exclude_objects=["person"]
      - "猫或狗的照片"      → keyword="猫狗", objects=["cat","dog"]
      - "植物相关的照片"    → keyword="植物", objects=["potted plant"]
    """
    pass  # implemented in _execute_tool


@tool
def create_album_tool(
    name: str,
    description: str = "",
) -> dict:
    """Create a new album. Call when the user wants to organize photos or create a collection.

    Args:
        name: Album name
        description: Album description (optional)
    """
    pass


@tool
def add_to_album(
    album_id: str,
    photo_ids: List[str],
) -> dict:
    """Add photos to an existing album. Needs an album_id (from recently created album or album list).

    Args:
        album_id: Album ID
        photo_ids: List of photo IDs to add
    """
    pass


@tool
def list_albums() -> dict:
    """List all albums for the current user. Call when the user asks ''what albums do I have.''"""
    pass


@tool
def get_stats() -> dict:
    """Get photo statistics. Call when the user asks ''how many photos do I have'' or ''how much storage.''"""
    pass


@tool
def analyze_image(
    query: str = "",
) -> dict:
    """Analyze the photo the user just uploaded. Call when the user uploads an image and asks about its contents.

    Args:
        query: What the user wants to know about the image, e.g. "what is in this photo" or "what objects are here"
    """
    pass


# Tool registry
TOOLS = [search_photos, create_album_tool, add_to_album, list_albums, get_stats, analyze_image]

TOOL_MAP = {
    "search_photos": search_photos,
    "create_album_tool": create_album_tool,
    "add_to_album": add_to_album,
    "list_albums": list_albums,
    "get_stats": get_stats,
    "analyze_image": analyze_image,
}


# --- Tool executor ----------------------------------------------------------


def _execute_tool(
    tool_name: str,
    tool_args: dict,
    db: Session,
    owner_id: str,
    image_bytes: Optional[bytes] = None,
) -> str:
    """Execute a tool call, return JSON string result."""
    try:
        if tool_name == "search_photos":
            keyword = tool_args.get("keyword", "")
            person_name = tool_args.get("person_name")
            objects = tool_args.get("objects")
            top_k = tool_args.get("top_k", 20)
            exclude_objects = tool_args.get("exclude_objects")
            match_all = tool_args.get("match_all", False)
            only = tool_args.get("only", False)

            if not keyword and not person_name and not objects:
                keyword = "photo"

            # Phase 1: CLIP search
            results = clip_search_by_text(
                db=db,
                query_text=keyword,
                top_k=max(min(top_k, 50), 100 if objects else 50),
                owner_id=owner_id,
            )

            # Phase 1.5: person-name filtering
            if person_name and results:
                from app.services.search_service import search_faces_by_name
                face_ids = set(search_faces_by_name(db, person_name, owner_id))
                if face_ids:
                    results = [r for r in results if r["photo_id"] in face_ids]

            # Phase 2: YOLO tag filtering
            # Phase 2: Direct YOLO tag search (independent of CLIP results)
            if objects:
                from uuid import UUID as _UUID
                from sqlalchemy import or_
                from app.models.photo import Photo

                # Build label pattern for all target objects
                target_lower = {o.lower() for o in objects}
                owner_uuid = _UUID(owner_id) if owner_id else None

                # Query ImageDescription with photos that have non-null tags
                tag_rows = (
                    db.query(ImageDescription.photo_id, ImageDescription.tags)
                    .join(Photo, Photo.id == ImageDescription.photo_id)
                    .filter(
                        ImageDescription.tags.isnot(None),
                        Photo.is_deleted == False,
                    )
                    .all()
                )
                if owner_uuid:
                    # Re-query with owner filter
                    tag_rows = (
                        db.query(ImageDescription.photo_id, ImageDescription.tags)
                        .join(Photo, Photo.id == ImageDescription.photo_id)
                        .filter(
                            ImageDescription.tags.isnot(None),
                            Photo.owner_id == owner_uuid,
                            Photo.is_deleted == False,
                        )
                        .all()
                    )

                tag_results = []
                for row in tag_rows:
                    tags = row.tags
                    if not isinstance(tags, dict):
                        continue
                    summary = tags.get("summary", [])
                    if not isinstance(summary, list):
                        continue
                    matched = []
                    excluded = []
                    all_labels = set()
                    for item in summary:
                        if isinstance(item, dict) and item.get("label"):
                            label = item["label"].lower()
                            all_labels.add(label)
                            # Check inclusion (objects list)
                            for to in target_lower:
                                if to == label or to in label or label in to:
                                    matched.append(item["label"])
                            # Check exclusion (exclude_objects list)
                            if exclude_objects:
                                for eo in {e.lower() for e in exclude_objects}:
                                    if eo == label or eo in label or label in eo:
                                        excluded.append(item["label"])
                    # Apply AND/OR/NOT logic
                    should_include = bool(matched)
                    if should_include and exclude_objects and excluded:
                        should_include = False  # NOT: excluded object present
                    if should_include and match_all:
                        matched_set = set(matched)
                        matched_normalized = set()
                        for m in matched_set:
                            ml = m.lower()
                            for to in target_lower:
                                if to == ml or to in ml or ml in to:
                                    matched_normalized.add(to)
                        if matched_normalized != target_lower:
                            should_include = False  # AND: not all objects present
                    if should_include and only:
                        extra = all_labels - target_lower
                        if extra:
                            should_include = False  # ONLY: photo has extra objects
                    if should_include:
                        tag_results.append({
                            "photo_id": str(row.photo_id),
                            "score": 0.5,
                            "matched_objects": list(set(matched)),
                            "source": "yolo_tag",
                            "all_detections": list(all_labels),
                        })

                # Merge tag results with CLIP results (tag results take priority)
                clip_ids = {r["photo_id"] for r in results}
                for tr in tag_results:
                    if tr["photo_id"] not in clip_ids:
                        results.append(tr)

                # Re-sort: matched objects count desc, then CLIP score desc
                results.sort(key=lambda x: (
                    -len(x.get("matched_objects", [])),
                    -x.get("score", 0)
                ))

            # Phase 3: Person-name filtering (unchanged)

            return json.dumps({
                "found": len(results),
                "photos": [
                    {
                        "id": r["photo_id"],
                        "score": round(r.get("score", 0), 3),
                        **({"matched_objects": r.get("matched_objects")} if r.get("matched_objects") else {}),
                    }
                    for r in results[:top_k]
                ],
            }, ensure_ascii=False)

        elif tool_name == "create_album_tool":
            name = tool_args.get("name", "unnamed album")
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

        elif tool_name == "analyze_image":
            query = tool_args.get("query", "")
            result: dict = {"objects": [], "faces": [], "scene": ""}

            # 1. YOLO detection
            if image_bytes:
                try:
                    from app.services.detection_service import detect_objects_from_bytes, get_detection_summary
                    det_result = detect_objects_from_bytes(image_bytes, confidence_threshold=0.25)
                    if det_result.get("success"):
                        summary = get_detection_summary(det_result["detections"])
                        result["objects"] = [
                            {"label": s["label"], "count": s["count"], "confidence": round(s["max_confidence"], 2)}
                            for s in summary
                        ]
                except Exception as e:
                    logger.warning(f"YOLO detection failed in analyze_image: {e}")

                # 2. CLIP scene classification
                try:
                    from app.services.ai_providers.embedding import get_image_embedding
                    embedding = get_image_embedding(image_bytes)
                    if embedding:
                        result["clip_embedding_dim"] = len(embedding)
                except Exception as e:
                    logger.warning(f"CLIP embedding failed in analyze_image: {e}")

                # 3. Face detection via InsightFace (best-effort)
                try:
                    from app.services.face_cluster_service import cosine_similarity
                    _ = cosine_similarity  # just check import, actual face detection is async
                    result["face_note"] = "face detection available for offline processing"
                except Exception:
                    pass
            else:
                result["error"] = "no image provided"

            return json.dumps(result, ensure_ascii=False)

        else:
            return json.dumps({"error": f"unknown tool: {tool_name}"})

    except Exception as e:
        logger.error(f"Tool execution failed [{tool_name}]: {e}")
        return json.dumps({"error": str(e)})


# --- Agent main loop --------------------------------------------------------


def run_llm_agent(
    user_message: str,
    db: Session,
    owner_id: str,
    session_id: str,
    history: Optional[List[dict]] = None,
    image_bytes: Optional[bytes] = None,
) -> dict:
    """Execute the LLM agent conversation.

    Returns:
        {"reply": str, "results": list, "total": int, "tool_calls": list}
    """
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if history:
        for msg in history[-20:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

    user_content = user_message
    if image_bytes:
        user_content = f"[User uploaded an image] {user_message}" if user_message else "[User uploaded an image, please analyze it]"
    messages.append(HumanMessage(content=user_content))

    response = llm_with_tools.invoke(messages)

    tool_results_for_frontend = []
    all_photos = []

    for _round in range(3):
        if not response.tool_calls:
            break

        tool_messages = []
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            logger.info(f"Agent calling tool: {tool_name}({tool_args})")
            result_json = _execute_tool(tool_name, tool_args, db, owner_id, image_bytes=image_bytes)
            result_data = json.loads(result_json)

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
        response = llm_with_tools.invoke(messages)

    reply = response.content if hasattr(response, 'content') else str(response)

    return {
        "reply": reply,
        "results": all_photos[:20],
        "total": len(all_photos),
        "tool_calls": tool_results_for_frontend,
    }
