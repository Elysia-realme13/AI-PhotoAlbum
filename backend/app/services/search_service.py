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
from datetime import datetime, timedelta
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
    r"干爹|干妈|养父|养母|继父|继母"

    r")",
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
    tokens = re.split(r"[\s,，。！？、；：()（）【】《》〝〞]+", text)

    result = [t.strip() for t in tokens if len(t.strip()) > 1]
    if len(result) <= 1 and len(text) > 5 and _is_mostly_chinese(text):
        return _chinese_bigram_tokenize(text)
    return result


def _is_mostly_chinese(text: str, threshold: float = 0.6) -> bool:
    if not text:
        return False
    chinese = sum(1 for c in text if "一" <= c <= "鿿")
    return chinese / len(text) >= threshold


def _chinese_bigram_tokenize(text: str) -> List[str]:
    bigrams = []
    seen = set()
    chars = "".join(c for c in text if "一" <= c <= "鿿")
    if len(chars) <= 1:
        return [text.strip()]
    for i in range(len(chars) - 1):
        bg = chars[i:i + 2]
        if bg not in seen:
            seen.add(bg)
            bigrams.append(bg)
    if len(bigrams) <= 1:
        return [text.strip()]
    return bigrams
def _is_mostly_chinese(text: str, threshold: float = 0.6) -> bool:
    if not text:
        return False
    chinese = sum(1 for c in text if "一" <= c <= "鿿")
    return chinese / len(text) >= threshold


def _chinese_bigram_tokenize(text: str) -> List[str]:
    bigrams = []
    seen = set()
    chars = "".join(c for c in text if "一" <= c <= "鿿")
    if len(chars) <= 1:
        return [text.strip()]
    for i in range(len(chars) - 1):
        bg = chars[i:i + 2]
        if bg not in seen:
            seen.add(bg)
            bigrams.append(bg)
    if len(bigrams) <= 1:
        return [text.strip()]
    return bigrams
def is_person_query(nouns: List[str], person_names: List[str]) -> bool:
    return len(person_names) > 0


# CLIP 向量检索

def clip_search_by_text(
    db: Session,
    query_text: str,
    top_k: int = 50,
    owner_id=None,
    photo_ids=None,
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
    return _vector_search(db, vector_str, top_k, owner_id, photo_ids=photo_ids)


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


def _vector_search(db: Session, vector_str: str, top_k: int, owner_id, photo_ids=None) -> List[dict]:
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

    if photo_ids and len(photo_ids) > 0:
        from sqlalchemy import bindparam
        placeholders = ",".join(f":pid_{i}" for i in range(len(photo_ids)))
        sql_str += f" AND iv.photo_id IN ({placeholders})"
        for i, pid in enumerate(photo_ids):
            params[f"pid_{i}"] = pid

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
    photo_ids=None,
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
    return _vector_search(db, vector_str, top_k, owner_id, photo_ids=photo_ids)


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

_SEASON_MONTHS = {"春": (3, 5), "夏": (6, 8), "秋": (9, 11), "冬": (12, 2)}
_RELATIVE_YEARS = {"去年": (-1, 0), "前年": (-2, 0), "今年": (0, 0), "上一年": (-1, 0), "前一年": (-1, 0)}
_RELATIVE_MONTHS = {"上个月": (0, -1), "这个月": (0, 0), "本月": (0, 0)}
_RE_N_YEARS_AGO = re.compile(r"(\d{1,2})\s*年前")
_RE_YEAR = re.compile(r"(\d{4})\s*年")
_RE_MONTH = re.compile(r"(\d{1,2})\s*月")
_RE_SEASON = re.compile(r"(春|夏|秋|冬)(?:天|季)?")

# Location suffixes for recognizing place names
_LOCATION_SUFFIXES = {
    "省", "市", "县", "区", "镇", "乡", "村",
    "路", "街", "巷", "弄", "道",
    "公园", "广场", "大厦", "中心", "大楼",
    "山", "河", "湖", "海", "岛", "湾",
    "北京", "上海", "天津", "重庆",
}


def extract_time_range(text, reference_date=None):
    # Extract time range from Chinese query text.
    # Supports: "去年夏天", "2024年", "上个月", "前年", "今年春天", "3月", "三年前"
    # Returns (start_datetime, end_datetime) or (None, None)
    if reference_date is None:
        reference_date = datetime.now()
    now = reference_date
    year = now.year
    month = now.month

    # 1. "N年前"
    m = _RE_N_YEARS_AGO.search(text)
    if m:
        n = int(m.group(1))
        ty = year - n
        return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))

    # 2. Relative year + season (e.g. "去年夏天")
    for kw, (dy, dm) in _RELATIVE_YEARS.items():
        if kw in text:
            ty = year + dy
            sm = _RE_SEASON.search(text)
            if sm:
                season = sm.group(1)
                sm_val, em_val = _SEASON_MONTHS[season]
                if season == "冬":
                    return (datetime(ty, sm_val, 1), datetime(ty + 1, em_val, 28, 23, 59, 59))
                return (datetime(ty, sm_val, 1), datetime(ty, em_val, 30, 23, 59, 59))
            return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))

    # 3. Relative month (e.g. "上个月")
    for kw, (dy, dm) in _RELATIVE_MONTHS.items():
        if kw in text:
            target = datetime(year + dy, month + dm, 1)
            if target.month == 12:
                end = datetime(target.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(target.year, target.month + 1, 1) - timedelta(seconds=1)
            return (target, end)

    # 4. Season (current year, e.g. "夏天")
    sm = _RE_SEASON.search(text)
    if sm:
        season = sm.group(1)
        sm_val, em_val = _SEASON_MONTHS[season]
        ym = _RE_YEAR.search(text)
        ty = int(ym.group(1)) if ym else year
        if season == "冬":
            return (datetime(ty, sm_val, 1), datetime(ty + 1, em_val, 28, 23, 59, 59))
        return (datetime(ty, sm_val, 1), datetime(ty, em_val, 30, 23, 59, 59))

    # 5. Absolute year "2024年"
    ym = _RE_YEAR.search(text)
    if ym:
        ty = int(ym.group(1))
        mm = _RE_MONTH.search(text)
        if mm:
            tm = int(mm.group(1))
            if tm == 12:
                end = datetime(ty + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(ty, tm + 1, 1) - timedelta(seconds=1)
            return (datetime(ty, tm, 1), end)
        return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))

    # 6. Month only "3月" (current year)
    mm = _RE_MONTH.search(text)
    if mm:
        tm = int(mm.group(1))
        if tm == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, tm + 1, 1) - timedelta(seconds=1)
        return (datetime(year, tm, 1), end)

    return (None, None)


def filter_photos_by_time(db, owner_id, start=None, end=None):
    # Filter photos by photo_time range, return matching photo IDs
    if start is None and end is None:
        return []
    from app.models.photo import Photo
    import uuid as _uuid
    owner_uuid = _uuid.UUID(str(owner_id))
    q = db.query(Photo.id).filter(Photo.owner_id == owner_uuid, Photo.is_deleted == False)
    if start:
        q = q.filter(Photo.photo_time >= start)
    if end:
        q = q.filter(Photo.photo_time <= end)
    return [str(row[0]) for row in q.all()]


def extract_location_keywords(text, nouns):
    # Extract likely location keywords from nouns list
    locations = []
    for loc in _LOCATION_SUFFIXES:
        if loc in text:
            locations.append(loc)
    for noun in nouns:
        for suffix in _LOCATION_SUFFIXES:
            if len(suffix) > 1 and noun.endswith(suffix):
                if noun not in locations:
                    locations.append(noun)
                break
    return locations[:5]


def filter_photos_by_location(db, owner_id, keywords):
    # Filter photos by location keywords in photo_metadata
    if not keywords:
        return []
    from app.models.photo import Photo, PhotoMetadata
    import uuid as _uuid
    owner_uuid = _uuid.UUID(str(owner_id))
    conditions = []
    for kw in keywords:
        pattern = "%" + kw + "%"
        conditions.append(PhotoMetadata.country.like(pattern))
        conditions.append(PhotoMetadata.province.like(pattern))
        conditions.append(PhotoMetadata.city.like(pattern))
        conditions.append(PhotoMetadata.district.like(pattern))
        conditions.append(PhotoMetadata.address.like(pattern))
    rows = (
        db.query(PhotoMetadata.photo_id)
        .join(Photo, Photo.id == PhotoMetadata.photo_id)
        .filter(Photo.owner_id == owner_uuid, Photo.is_deleted == False, or_(*conditions))
        .distinct()
        .all()
    )
    return [str(row[0]) for row in rows]

# ------------------------------------------------------------------
#  时间表达式解析与过滤
# ------------------------------------------------------------------

_SEASON_MONTHS = {"春": (3, 5), "夏": (6, 8), "秋": (9, 11), "冬": (12, 2)}
_RELATIVE_YEARS = {"去年": (-1, 0), "前年": (-2, 0), "今年": (0, 0)}
_RELATIVE_MONTHS = {"上个月": (0, -1), "这个月": (0, 0), "本月": (0, 0)}
_RE_N_YEARS_AGO = re.compile(r"(\d{1,2}|[一二三四五六七八九十]{1,2})\s*年前")
_RE_YEAR = re.compile(r"(\d{4})\s*年")
_RE_MONTH = re.compile(r"(\d{1,2})\s*月")
_RE_SEASON = re.compile(r"(春|夏|秋|冬)(?:天|季)?")
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _parse_cn_number(raw):
    if raw.isdigit():
        return int(raw)
    if len(raw) == 1:
        return _CN_DIGITS.get(raw, 0)
    if raw[0] == "十":
        return 10 + _CN_DIGITS.get(raw[1], 0)
    if raw[1] == "十":
        return _CN_DIGITS.get(raw[0], 0) * 10
    return 0


def extract_time_range(text, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()
    now = reference_date
    year = now.year
    month = now.month
    m = _RE_N_YEARS_AGO.search(text)
    if m:
        n = _parse_cn_number(m.group(1))
        if n > 0:
            ty = year - n
            return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))
    for kw, (dy, dm) in _RELATIVE_YEARS.items():
        if kw in text:
            ty = year + dy
            sm = _RE_SEASON.search(text)
            if sm:
                season = sm.group(1)
                sm_val, em_val = _SEASON_MONTHS[season]
                if season == "冬":
                    return (datetime(ty, sm_val, 1), datetime(ty + 1, em_val, 28, 23, 59, 59))
                return (datetime(ty, sm_val, 1), datetime(ty, em_val, 30, 23, 59, 59))
            return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))
    for kw, (dy, dm) in _RELATIVE_MONTHS.items():
        if kw in text:
            target = datetime(year + dy, month + dm, 1)
            if target.month == 12:
                end = datetime(target.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(target.year, target.month + 1, 1) - timedelta(seconds=1)
            return (target, end)
    sm = _RE_SEASON.search(text)
    if sm:
        season = sm.group(1)
        sm_val, em_val = _SEASON_MONTHS[season]
        ym = _RE_YEAR.search(text)
        ty = int(ym.group(1)) if ym else year
        if season == "冬":
            return (datetime(ty, sm_val, 1), datetime(ty + 1, em_val, 28, 23, 59, 59))
        return (datetime(ty, sm_val, 1), datetime(ty, em_val, 30, 23, 59, 59))
    ym = _RE_YEAR.search(text)
    if ym:
        ty = int(ym.group(1))
        mm = _RE_MONTH.search(text)
        if mm:
            tm = int(mm.group(1))
            if tm == 12:
                end = datetime(ty + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(ty, tm + 1, 1) - timedelta(seconds=1)
            return (datetime(ty, tm, 1), end)
        return (datetime(ty, 1, 1), datetime(ty, 12, 31, 23, 59, 59))
    mm = _RE_MONTH.search(text)
    if mm:
        tm = int(mm.group(1))
        if tm == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, tm + 1, 1) - timedelta(seconds=1)
        return (datetime(year, tm, 1), end)
    return (None, None)


def filter_photos_by_time(db, owner_id, start=None, end=None):
    if start is None and end is None:
        return []
    from app.models.photo import Photo
    import uuid as _uuid
    owner_uuid = _uuid.UUID(str(owner_id))
    q = db.query(Photo.id).filter(Photo.owner_id == owner_uuid, Photo.is_deleted == False)
    if start:
        q = q.filter(Photo.photo_time >= start)
    if end:
        q = q.filter(Photo.photo_time <= end)
    return [str(row[0]) for row in q.all()]


# ------------------------------------------------------------------
#  地点提取与过滤
# ------------------------------------------------------------------

_LOCATION_SUFFIXES = {
    "省", "市", "县", "区", "镇", "乡", "村",
    "路", "街", "巷", "弄", "道",
    "公园", "广场", "大厦", "中心", "大楼",
    "山", "河", "湖", "海", "岛", "湾",
    "北京", "上海", "天津", "重庆",
}


def extract_location_keywords(text, nouns):
    locations = []
    for loc in _LOCATION_SUFFIXES:
        if loc in text:
            locations.append(loc)
    for noun in nouns:
        for suffix in _LOCATION_SUFFIXES:
            if len(suffix) > 1 and noun.endswith(suffix):
                if noun not in locations:
                    locations.append(noun)
                break
    return locations[:5]


def filter_photos_by_location(db, owner_id, keywords):
    if not keywords:
        return []
    from app.models.photo import Photo, PhotoMetadata
    from sqlalchemy import or_
    import uuid as _uuid
    owner_uuid = _uuid.UUID(str(owner_id))
    conditions = []
    for kw in keywords:
        pattern = "%" + kw + "%"
        conditions.append(PhotoMetadata.country.like(pattern))
        conditions.append(PhotoMetadata.province.like(pattern))
        conditions.append(PhotoMetadata.city.like(pattern))
        conditions.append(PhotoMetadata.district.like(pattern))
        conditions.append(PhotoMetadata.address.like(pattern))
    rows = (
        db.query(PhotoMetadata.photo_id)
        .join(Photo, Photo.id == PhotoMetadata.photo_id)
        .filter(Photo.owner_id == owner_uuid, Photo.is_deleted == False, or_(*conditions))
        .distinct()
        .all()
    )
    return [str(row[0]) for row in rows]


__all__ = [
    "extract_person_names",
    "extract_nouns",
    "is_person_query",
    "clip_search_by_text",
    "clip_search_by_image",
    "search_faces_by_name",
    "get_unnamed_candidates",
    "extract_time_range",
    "filter_photos_by_time",
    "extract_location_keywords",
    "filter_photos_by_location",
]
