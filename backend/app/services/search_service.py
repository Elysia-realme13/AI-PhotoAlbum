"""
文本检索服务

功能：
  1. 分词 + 词性标注 → 仅提取名词
  2. CLIP 向量相似度检索（pgvector cosine）
  3. 人称识别 → 人脸身份过滤
  4. 混合检索结果合并

依赖：jieba 分词、pgvector
"""
import re
import uuid as _uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.face import Face, FaceIdentity
from app.models.description import ImageVector
from app.models.photo import Photo

logger = logging.getLogger(__name__)

# 中文亲属称谓 / 人称模式
PERSON_PATTERNS = [
    r"(?:我?的?家?)?(爸爸|妈妈|爷爷|奶奶|外公|外婆|姥爷|姥姥|"
    r"祖父|祖母|哥哥|姐姐|弟弟|妹妹|儿子|女儿|老婆|老公|"
    r"丈夫|妻子|男友|女友|朋友|同事|同学|老师|学生|"
    r"侄子|侄女|外甥|外甥女|叔叔|阿姨|伯伯|伯母|"
    r"舅舅|舅妈|姑姑|姑父|岳父|岳母|公公|婆婆|"
    r"堂哥|堂姐|堂弟|堂妹|表哥|表姐|表弟|表妹|"
    r"干爹|干妈|养父|养母|继父|继母|"
    r"[\u4e00-\u9fff]{2,4})",
]

_person_regex = re.compile("|".join(f"({p})" for p in PERSON_PATTERNS))


def extract_person_names(text: str) -> List[str]:
    """使用正则从文本中提取人称/亲属称谓"""
    names = []
    for match in _person_regex.finditer(text):
        for group in match.groups():
            if group:
                names.append(group.strip())
    return list(set(names))


def extract_nouns(text: str) -> List[str]:
    """
    使用 jieba 分词 + 词性标注，提取名词
    """
    try:
        import jieba.posseg as pseg
    except ImportError:
        logger.warning("jieba 未安装，使用简单分词")
        return _simple_tokenize(text)

    NOUN_TAGS = {"n", "nr", "nr1", "nr2", "nrj", "nrf", "ns", "nsf", "nt", "nz", "nl", "ng"}
    words = pseg.cut(text)
    nouns = []
    for word, flag in words:
        if flag in NOUN_TAGS and len(word.strip()) > 0:
            nouns.append(word.strip())

    seen = set()
    unique_nouns = []
    for n in nouns:
        if n not in seen:
            seen.add(n)
            unique_nouns.append(n)
    return unique_nouns


def _simple_tokenize(text: str) -> List[str]:
    tokens = re.split(r"[\s,，。！？、；：()（）【】《》\"'\"']+", text)
    return [t.strip() for t in tokens if len(t.strip()) > 1]


def is_person_query(nouns: List[str], person_names: List[str]) -> bool:
    return len(person_names) > 0


# CLIP 向量检索

def clip_search_by_text(
    db: Session,
    query_text: str,
    top_k: int = 50,
    owner_id=None,
) -> List[dict]:
    """
    使用文本查询向量在 ImageVector 表中检索相似照片
    """
    try:
        query_vector = _get_query_embedding(query_text)
    except Exception:
        logger.warning("embedding 模型不可用，回退到 tag 文本匹配")
        return _tag_fallback_search(db, query_text, top_k, owner_id)

    if query_vector is None:
        return _tag_fallback_search(db, query_text, top_k, owner_id)

    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
    return _vector_search(db, vector_str, top_k, owner_id)


def _get_query_embedding(text: str) -> Optional[List[float]]:
    """
    调用 embedding 模型将文本转为 512 维向量
    """
    try:
        from app.services.ai_providers.embedding import get_embedding
        return get_embedding(text)
    except (ImportError, Exception) as e:
        logger.debug(f"embedding 模型加载失败: {e}")
        return None


def _vector_search(db: Session, vector_str: str, top_k: int, owner_id) -> List[dict]:
    """通用的 pgvector cosine 相似度检索"""
    sql_str = """
        SELECT iv.photo_id,
               1 - (iv.embedding <=> :query_vec::vector) AS cosine_similarity
        FROM image_vectors iv
        WHERE iv.embedding IS NOT NULL
    """
    params = {"query_vec": vector_str}

    if owner_id:
        owner_str = str(owner_id)
        sql_str += """
            AND iv.photo_id IN (
                SELECT p.id FROM photos p
                WHERE p.owner_id = :owner_id::uuid AND p.is_deleted = false
            )
        """
        params["owner_id"] = owner_str

    sql_str += " ORDER BY cosine_similarity DESC LIMIT :limit_val"
    params["limit_val"] = top_k

    try:
        rows = db.execute(text(sql_str), params).fetchall()
    except Exception as e:
        logger.error(f"pgvector 检索失败: {e}")
        return []

    return [{"photo_id": str(row[0]), "score": float(row[1])} for row in rows]


def clip_search_by_image(
    db: Session,
    image_bytes: bytes,
    top_k: int = 50,
    owner_id=None,
) -> List[dict]:
    """使用图片查询向量在 ImageVector 表中检索相似照片"""
    try:
        from app.services.ai_providers.embedding import get_image_embedding
        query_vector = get_image_embedding(image_bytes)
    except Exception as e:
        logger.warning(f"图片 embedding 失败: {e}")
        return []

    if query_vector is None:
        return []

    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
    return _vector_search(db, vector_str, top_k, owner_id)


def _tag_fallback_search(
    db: Session,
    query_text: str,
    top_k: int = 50,
    owner_id=None,
) -> List[dict]:
    """
    降级方案：使用 description / tags 文本 LIKE 匹配
    """
    from sqlalchemy import or_, cast, String
    from app.models.description import ImageDescription

    keywords = extract_nouns(query_text)
    if not keywords:
        keywords = [w for w in query_text.split() if len(w) > 1][:3]

    conditions = []
    for kw in keywords[:3]:
        kw_pattern = f"%{kw}%"
        conditions.append(ImageDescription.description.like(kw_pattern))
        conditions.append(cast(ImageDescription.tags, String).like(kw_pattern))

    query = db.query(ImageDescription).filter(or_(*conditions))

    if owner_id:
        owner_uuid = _uuid.UUID(str(owner_id))
        query = query.join(Photo).filter(
            Photo.owner_id == owner_uuid,
            Photo.is_deleted == False,
        )

    descriptions = query.limit(top_k).all()
    return [{"photo_id": str(d.photo_id), "score": 0.5} for d in descriptions]


# 人脸身份照片检索

def search_faces_by_name(
    db: Session,
    person_name: str,
    owner_id,
) -> List[str]:
    """
    根据人称查找对应聚类的照片 ID 列表
    """
    from app.services.name_confirmation_service import find_clusters_by_name
    clusters = find_clusters_by_name(db, owner_id, person_name)
    photo_ids = []
    for cluster in clusters:
        photo_ids.extend(cluster["photo_ids"])
    return list(set(photo_ids))


def get_unnamed_candidates(
    db: Session,
    owner_id,
    top_k: int = 5,
    min_face_count: int = 1,
) -> List[dict]:
    """
    获取尚未命名、出现频次最高的候选聚类
    """
    from app.services.face_cluster_service import get_unamed_clusters
    return get_unamed_clusters(db, owner_id, min_face_count, top_k)


__all__ = [
    "extract_person_names",
    "extract_nouns",
    "is_person_query",
    "clip_search_by_text",
    "clip_search_by_image",
    "search_faces_by_name",
    "get_unnamed_candidates",
]
