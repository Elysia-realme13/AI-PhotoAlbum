"""
LangGraph search agent

Implements "description -> photos" hybrid search with time/location filtering.
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.services.search_service import (
    extract_nouns, extract_person_names, clip_search_by_text,
    clip_search_by_image,
    search_faces_by_name, get_unnamed_candidates,
    extract_time_range, filter_photos_by_time,
    extract_location_keywords, filter_photos_by_location,
)

logger = logging.getLogger(__name__)


class SearchState(TypedDict):
    query: str
    owner_id: Optional[str]
    session_id: Optional[str]
    image_bytes: Optional[bytes]
    nouns: List[str]
    person_names: List[str]
    time_start: Optional[str]
    time_end: Optional[str]
    location_keywords: List[str]
    pre_filtered_ids: List[str]
    person_photo_ids: List[str]
    clip_results: List[dict]
    merged_results: List[dict]
    needs_confirmation: bool
    pending_candidates: List[dict]
    error: Optional[str]


def _get_db(config: Optional[RunnableConfig]) -> Optional[Session]:
    if config and "configurable" in config:
        return config["configurable"].get("db")
    return None


def extract_entities(state: SearchState, config: RunnableConfig) -> SearchState:
    query = state.get("query", "")
    if not query:
        state["error"] = "empty query"
        return state
    state["nouns"] = extract_nouns(query)
    state["person_names"] = extract_person_names(query)
    return state


def extract_time_location(state: SearchState, config: RunnableConfig) -> SearchState:
    query = state.get("query", "")
    if not query:
        return state
    from datetime import datetime
    time_start, time_end = extract_time_range(query, datetime.now())
    state["time_start"] = time_start.isoformat() if time_start else None
    state["time_end"] = time_end.isoformat() if time_end else None
    nouns = state.get("nouns", [])
    state["location_keywords"] = extract_location_keywords(query, nouns)
    return state


def pre_filter(state: SearchState, config: RunnableConfig) -> SearchState:
    db = _get_db(config)
    if not db:
        return state
    owner_id = state.get("owner_id")
    state["pre_filtered_ids"] = []

    time_ids = None
    loc_ids = None

    time_start_str = state.get("time_start")
    time_end_str = state.get("time_end")
    if time_start_str or time_end_str:
        from datetime import datetime
        ts = datetime.fromisoformat(time_start_str) if time_start_str else None
        te = datetime.fromisoformat(time_end_str) if time_end_str else None
        time_ids = filter_photos_by_time(db, owner_id, start=ts, end=te)

    loc_keywords = state.get("location_keywords", [])
    if loc_keywords:
        loc_ids = filter_photos_by_location(db, owner_id, loc_keywords)

    # Merge: intersect if both filters applied
    if time_ids is not None and loc_ids is not None:
        time_set = set(time_ids)
        state["pre_filtered_ids"] = [pid for pid in loc_ids if pid in time_set]
    elif time_ids is not None:
        state["pre_filtered_ids"] = time_ids
    elif loc_ids is not None:
        state["pre_filtered_ids"] = loc_ids

    return state


def recognize_person(state: SearchState, config: RunnableConfig) -> SearchState:
    db = _get_db(config)
    person_names = state.get("person_names", [])
    owner_id = state.get("owner_id")
    state["needs_confirmation"] = False
    state["pending_candidates"] = []
    state["person_photo_ids"] = []
    if not person_names:
        return state
    found_any = False
    for name in person_names:
        photo_ids = search_faces_by_name(db, name, owner_id)
        if photo_ids:
            state["person_photo_ids"].extend(photo_ids)
            found_any = True
    if not found_any:
        candidates = get_unnamed_candidates(db, owner_id, top_k=5)
        if candidates:
            state["needs_confirmation"] = True
            state["pending_candidates"] = candidates
    return state


def clip_search(state: SearchState, config: RunnableConfig) -> SearchState:
    db = _get_db(config)
    query = state.get("query", "")
    nouns = state.get("nouns", [])
    owner_id = state.get("owner_id")
    image_bytes = state.get("image_bytes")
    pre_filtered = state.get("pre_filtered_ids")

    photo_ids = pre_filtered if pre_filtered else None
    if image_bytes:
        state["clip_results"] = clip_search_by_image(
            db, image_bytes, top_k=100, owner_id=owner_id, photo_ids=photo_ids
        )
    else:
        search_text = " ".join(nouns[:5]) if nouns else query
        state["clip_results"] = clip_search_by_text(
            db, search_text, top_k=100, owner_id=owner_id, photo_ids=photo_ids
        )
    return state


def merge_results(state: SearchState, config: RunnableConfig) -> SearchState:
    person_ids = set(state.get("person_photo_ids", []))
    clip_results = state.get("clip_results", [])
    if not clip_results:
        state["merged_results"] = []
        return state
    if person_ids:
        merged = [r for r in clip_results if r["photo_id"] in person_ids]
        score_map = {r["photo_id"]: r["score"] for r in clip_results}
        for pid in person_ids:
            if pid not in score_map:
                merged.append({"photo_id": pid, "score": 0.3})
        state["merged_results"] = merged
    else:
        state["merged_results"] = clip_results
    state["merged_results"].sort(key=lambda x: -x["score"])
    state["merged_results"] = state["merged_results"][:50]
    return state


def build_search_graph():
    return _FallbackGraph()


class _FallbackGraph:
    def invoke(self, input_state: Dict[str, Any], config: Dict = None) -> Dict[str, Any]:
        state = dict(input_state)
        db = config.get("configurable", {}).get("db") if config else None
        if not db:
            state["error"] = "missing db session"
            return state
        nodes = [
            extract_entities,
            extract_time_location,
            pre_filter,
            recognize_person,
            clip_search,
            merge_results,
        ]
        for node in nodes:
            state = node(state, config)
            if state.get("error"):
                break
        return state


_search_graph = None


def run_search_agent(
    query: str, db: Session,
    owner_id: Optional[str] = None,
    session_id: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    global _search_graph
    if _search_graph is None:
        _search_graph = build_search_graph()
    initial_state: SearchState = {
        "query": query,
        "owner_id": str(owner_id) if owner_id else None,
        "session_id": session_id,
        "image_bytes": image_bytes,
        "nouns": [], "person_names": [],
        "time_start": None, "time_end": None,
        "location_keywords": [], "pre_filtered_ids": [],
        "person_photo_ids": [], "clip_results": [],
        "merged_results": [],
        "needs_confirmation": False,
        "pending_candidates": [],
        "error": None,
    }
    return _search_graph.invoke(initial_state, config={"configurable": {"db": db}})


__all__ = ["SearchState", "build_search_graph", "run_search_agent"]
