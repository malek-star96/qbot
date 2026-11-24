import asyncio
import re

import ai
import answers
from progress import Progress
from qureo import Qureo

MAX_ATTEMPTS = 5
MAX_STEPS = 200


def _clean(code: str) -> str:
    code = (code or "").strip()
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", code, re.S)
    return (m.group(1) if m else code).strip()


async def _apply(q, ans, opts) -> bool:
    if not ans:
        return False
    t = ans.get("type")
    if t == "text":
        return await q.click_option(ans.get("value", ""))
    if t == "multi":
        hit = False
        for v in ans.get("values", []):
            hit = await q.click_option(v) or hit
        return hit
    if t in ("code", "partial", "fill"):
        code = ans.get("value") or ans.get("full_code") or ""
        return await q.type_code(code) if code.strip() else False
    return False


async def _answer_for(text, opts, feedback):
    ans = answers.lookup_cache if False else None
    if feedback:
        if opts:
            ans = await ai.answer(text, opts, feedback)
        if not ans:
            ans = {"type": "code", "value": _clean(await ai.solve(text, feedback))}
        return ans
    if opts:
        ans = await ai.answer(text, opts)
    return ans or {"type": "code", "value": _clean(await ai.solve(text))}


async def run(update, course, levels, creds):
    prog = Progress(await update.message.reply_text("بجهز…"), len(levels))
    q = Qureo()
    try:
        await q.start()
        await q.login(*creds)

        for level in levels:
            prog.current = f"المستوى {level}"
            await prog.push(force=True)

            data = await answers.level_data(course, level)
            try:
                await q.open_level(course, level)
            except Exception:
                prog.failed.append((str(level), "-", "فتح المستوى"))
                prog.done += 1
                await prog.push(force=True)
                continue

            level_failed = False
            count = len(await q.lessons())

            for li in range(count):
                les = await q.lessons()
                if li >= len(les):
                    break
                try:
                    await les[li].click()
                    await q.page.wait_for_timeout(2000)
                except Exception:
                    continue

                for _ in range(MAX_STEPS):
                    text, opts = await q.question()
                    if not text:
                        break

                    ans = answers.lookup(data, str(li + 1), text)
                    feedback = ""
                    ok = False

                    for attempt in range(1, MAX_ATTEMPTS + 1):
                        if attempt == 1 and ans:
                            pass
                        else:
                            if attempt > 1:
                                feedback = f"الإجابة دي رجعت غلط: {ans}"
                            ans = await _answer_for(text, opts, feedback)

                        if not await _apply(q, ans, opts):
                            await asyncio.sleep(1)
                            continue

                        v = await q.verdict()
                        if v == "UNKNOWN":
                            await asyncio.sleep(2)
                            v = await q.verdict()
                        if v == "OK":
                            ok = True
                            break
                        await asyncio.sleep(1)

                    if not ok:
                        level_failed = True
                        prog.failed.append((str(level), str(li + 1), text[:60]))

                    if not await q.next():
                        break

                await asyncio.sleep(2)

            prog.done += 1
            if not level_failed:
                prog.ac += 1
            await prog.push(force=True)
    finally:
        await q.close()