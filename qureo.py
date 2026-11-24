import os

from playwright.async_api import async_playwright

PORTAL = "https://me-portal.qureo.education"

SEL = {
    "email": "input[type=email], input[name*=mail], input[name*=login]",
    "pass": "input[type=password]",
    "submit": "button[type=submit]",
    "lesson": "a[href*='/lesson'], .lesson-item, [data-lesson]",
    "q_text": ".question, .quiz-question, [class*=question]",
    "option": ".choice, .option, [class*=choice] button, [class*=option]",
    "editor": ".cm-content, .monaco-editor, textarea.code, [contenteditable=true]",
    "next": "button[class*=next], [class*=next]",
    "correct": ".correct, [class*=correct], [class*=success]",
    "wrong": ".wrong, [class*=incorrect], [class*=error]",
}

ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]


async def _text(el) -> str:
    try:
        return (await el.inner_text()).strip() if el else ""
    except Exception:
        return ""


class Qureo:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.page = None

    async def start(self):
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=os.getenv("HEADLESS", "1") == "1", args=ARGS)
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 412, "height": 900})

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()

    async def login(self, handle: str, password: str):
        await self.page.goto(f"{PORTAL}/login", wait_until="domcontentloaded")
        await self.page.wait_for_selector(SEL["email"], timeout=20000)
        await self.page.fill(SEL["email"], handle)
        await self.page.fill(SEL["pass"], password)
        await self.page.click(SEL["submit"])
        await self.page.wait_for_timeout(6000)
        if "/login" in self.page.url:
            raise RuntimeError("الدخول فشل")

    async def open_level(self, course: str, level: int):
        from answers import chapter_id
        await self.page.goto(f"{PORTAL}/chapter/{chapter_id(course, level)}",
                             wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

    async def lessons(self):
        return await self.page.query_selector_all(SEL["lesson"])

    async def question(self):
        text = await _text(await self.page.query_selector(SEL["q_text"]))
        opts = [await _text(o) for o in await self.page.query_selector_all(SEL["option"])]
        return text, [o for o in opts if o]

    async def click_option(self, text: str) -> bool:
        for o in await self.page.query_selector_all(SEL["option"]):
            if await _text(o) == text:
                await o.click()
                await self.page.wait_for_timeout(900)
                return True
        return False

    async def type_code(self, code: str) -> bool:
        ed = await self.page.query_selector(SEL["editor"])
        if not ed:
            return False
        await ed.click()
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Delete")
        await self.page.keyboard.type(code, delay=8)
        return True

    async def verdict(self) -> str:
        await self.page.wait_for_timeout(1500)
        if await self.page.query_selector(SEL["correct"]):
            return "OK"
        if await self.page.query_selector(SEL["wrong"]):
            return "WRONG"
        return "UNKNOWN"

    async def next(self) -> bool:
        btn = await self.page.query_selector(SEL["next"])
        if not btn:
            return False
        try:
            await btn.click()
            await self.page.wait_for_timeout(1200)
            return True
        except Exception:
            return False