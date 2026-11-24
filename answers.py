import json
import re
import unicodedata
from pathlib import Path

import httpx

COURSE_DIR = {"js": "JavaScript", "py": "Python"}
BASE_ID = {"js": 90000, "py": 511000}
TASKS = Path("tasks.json")
RAW = ("https://raw.githubusercontent.com/vfggf95565/QUREO-Answers/"
       "main/{course}/{level}.json")

_cache = {}
_ids = {}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", s).strip()


def chapters(course: str):
    if course in _ids:
        return _ids[course]
    ids = None
    try:
        if TASKS.exists():
            raw = json.loads(TASKS.read_text(encoding="utf-8")).get(course)
            if isinstance(raw, list) and raw:
                ids = [int(x) for x in raw]
    except Exception:
        ids = None
    _ids[course] = ids
    return ids


def chapter_id(course: str, level: int) -> int:
    ids = chapters(course)
    if ids and 1 <= level <= len(ids):
        return ids[level - 1]
    return BASE_ID[course] + level


async def level_data(course: str, level: int):
    key = (course, level)
    if key in _cache:
        return _cache[key]
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(RAW.format(course=COURSE_DIR[course], level=level))
            data = r.json() if r.status_code == 200 else None
    except Exception:
        data = None
    _cache[key] = data
    return data


def lookup(data, lesson: str, question: str):
    if not data:
        return None
    bucket = data.get("lessons", {}).get(lesson)
    if not bucket:
        return None
    target = norm(question)
    for item in bucket.get("questions", {}).values():
        if norm(item.get("question")) == target:
            return item.get("answer")
    return None