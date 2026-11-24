import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from qureo import SEL, Qureo

load_dotenv()


async def dump(q, tag):
    try:
        Path(f"probe_{tag}.html").write_text(await q.page.content(), encoding="utf-8")
        await q.page.screenshot(path=f"probe_{tag}.png", full_page=True)
    except Exception as e:
        print("DUMP FAILED:", e)


async def main():
    q = Qureo()
    await q.start()
    try:
        try:
            await q.login(os.environ["Q_USER"], os.environ["Q_PASS"])
        except Exception as e:
            print("LOGIN FAILED:", repr(e))
            print("URL:", q.page.url)
            await dump(q, "login")
            return

        print("LOGIN OK:", q.page.url)
        try:
            await q.open_level(os.environ.get("Q_COURSE", "js"), 1)
        except Exception as e:
            print("OPEN FAILED:", repr(e))
            print("URL:", q.page.url)
            await dump(q, "open")
            return

        print("URL:", q.page.url)
        print("LESSONS:", len(await q.lessons()))
        t, o = await q.question()
        print("Q:", repr(t))
        print("OPTS:", o)
        print("EDITOR:", bool(await q.page.query_selector(SEL["editor"])))
        print("NEXT:", bool(await q.page.query_selector(SEL["next"])))
        await dump(q, "level")
    finally:
        await q.close()


asyncio.run(main())