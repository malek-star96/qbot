import time

FULL, EMPTY = "█", "░"


class Progress:
    def __init__(self, msg, total):
        self.msg = msg
        self.total = total
        self.done = 0
        self.ac = 0
        self.failed = []
        self.current = "-"
        self.last = 0

    def render(self):
        w = 18
        filled = int(w * self.done / self.total) if self.total else 0
        pct = int(100 * self.done / self.total) if self.total else 0
        return (f"<b>{FULL * filled}{EMPTY * (w - filled)} {pct}%</b>\n"
                f"خلصت {self.done}/{self.total} — ناجح {self.ac} | فشل {len(self.failed)}\n"
                f"بشغل دلوقتي: <code>{self.current}</code>")

    async def push(self, force=False):
        if not force and time.time() - self.last < 3:
            return
        self.last = time.time()
        try:
            await self.msg.edit_text(self.render(), parse_mode="HTML")
        except Exception:
            pass