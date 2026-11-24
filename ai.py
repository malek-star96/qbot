import json
import os
import re

import httpx

API = "https://api.venice.ai/api/v1/chat/completions"
MODEL = os.getenv("VENICE_MODEL", "qwen3-coder-480b-a35b-instruct-turbo")

SYSTEM_CODE = """أنت مبرمج محترف. اكتب الكود المطلوب بالظبط زي ما المسألة طالبة.
غطّي الحالات الحدية. ردك يبقى كود في بلوك واحد ``` فقط."""

SYSTEM_QUIZ = """أنت طالب خبير في منهج البرمجة الياباني للمرحلة الثانوية.
هتجيلك مسألة واختيارات. حدد الإجابة الصح.
لو الإجابة كود اكتب الكود، ولو اختيار اكتب نص الاختيار كما هو حرفيًا.
رد بـJSON فقط بالشكل:
{"type":"text","value":"نص الاختيار"}
أو
{"type":"code","value":"الكود"}
أو لو أكتر من اختيار:
{"type":"multi","values":["أ","ب"]}"""


async def _post(system: str, user: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": 3000,
    }
    headers = {"Authorization": f"Bearer {os.environ['VENICE_API_KEY']}"}
    async with httpx.AsyncClient(timeout=240) as c:
        r = await c.post(API, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def solve(problem: str, feedback: str = "") -> str:
    user = f"المسألة:\n{problem}"
    if feedback:
        user += f"\n\nمحاولاتك السابقة فشلت:\n{feedback}\nصلّح."
    return await _post(SYSTEM_CODE, user)


def _json(text: str):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


async def answer(question: str, options: list, feedback: str = ""):
    opts = "\n".join(f"- {o}" for o in options) or "(مسألة كود مفيش اختيارات)"
    user = f"السؤال:\n{question}\n\nالاختيارات:\n{opts}"
    if feedback:
        user += f"\n\nمحاولاتك السابقة فشلت:\n{feedback}\nصلّح."
    data = _json(await _post(SYSTEM_QUIZ, user))
    if not data:
        return None
    if data.get("type") == "text" and data.get("value") in options:
        return {"type": "text", "value": data["value"]}
    if data.get("type") == "multi":
        vals = [v for v in data.get("values", []) if v in options]
        return {"type": "multi", "values": vals} if vals else None
    if data.get("type") == "code" and data.get("value"):
        return {"type": "code", "value": data["value"]}
    return None