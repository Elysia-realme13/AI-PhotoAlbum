"""
LangGraph 妫€绱唬鐞?

瀹炵幇"鎻忚堪->鐓х墖"娣峰悎妫€绱笌浜鸿劯浜や簰寮忓懡鍚嶆祦绋嬨€?
"""

import logging
from typing import Any, Dict, List, Optional, TypedDict
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.services.search_service import (
    extract_nouns, extract_person_names, clip_search_by_text,
    search_faces_by_name, get_unnamed_candidates,
)

logger = logging.getLogger(__name__)


class SearchState(TypedDict):
    query: str
    owner_id: Optional[str]
    session_id: Optional[str]
    nouns: List[str]
    person_names: List[str]
    person_photo_ids: List[str]
    clip_results: List[dict]
    merged_results: List[dict]
    needs_confirmation: bool
    pending_candidates: List[dict]
    error: Optional[str]


def _get_db(config: Optional[RunnableConfig]) -> Optional[Session]:
    """从 LangGraph config 中提取 db session"""
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
    search_text = " ".join(nouns[:5]) if nouns else query
    state["clip_results"] = clip_search_by_text(db, search_text, top_k=100, owner_id=owner_id)
    return state


def merge_results(state: SearchState, config: RunnableConfig) -> SearchState:
    db = _get_db(config)
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
        for node in [extract_entities, recognize_person, clip_search, merge_results]:
            state = node(state, db)
            if state.get("error"):
                break
        return state


_search_graph = None


def run_search_agent(
    query: str, db: Session,
    owner_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    global _search_graph
    if _search_graph is None:
        _search_graph = build_search_graph()
    initial_state: SearchState = {
        "query": query,
        "owner_id": str(owner_id) if owner_id else None,
        "session_id": session_id,
        "nouns": [], "person_names": [],
        "person_photo_ids": [], "clip_results": [],
        "merged_results": [],
        "needs_confirmation": False,
        "pending_candidates": [],
        "error": None,
    }
    return _search_graph.invoke(initial_state, config={"configurable": {"db": db}})


__all__ = ["SearchState", "build_search_graph", "run_search_agent"]

