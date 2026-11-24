import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

import runner
from qureo import Qureo

load_dotenv()
logging.basicConfig(level=logging.INFO)

COURSES = {"js": "JavaScript", "py": "Python"}


def course_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(v, callback_data=f"crs:{k}") for k, v in COURSES.items()
    ]])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    ctx.user_data["step"] = "handle"
    await update.message.reply_text(
        "ابعت ايميل حساب كيريو:",
        reply_markup=ForceReply(selective=True))


async def pick_course(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["course"] = q.data.split(":", 1)[1]
    await q.edit_message_text(
        f"الكورس: {COURSES[ctx.user_data['course']]}\n\nابعت /run.")


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    step = ctx.user_data.get("step")
    text = update.message.text.strip()
    if not step:
        return

    if step == "handle":
        ctx.user_data["handle"] = text
        ctx.user_data["step"] = "password"
        return await update.message.reply_text(
            "ابعت الباس:", reply_markup=ForceReply(selective=True))

    if step == "password":
        ctx.user_data["password"] = text
        ctx.user_data["step"] = None
        try:
            await update.message.delete()
        except Exception:
            pass

        msg = await update.message.reply_text("بتأكد الدخول…")
        q = Qureo()
        try:
            await q.start()
            await asyncio.wait_for(q.login(ctx.user_data["handle"], text), 120)
            await msg.edit_text("الدخول شغال. اختار الكورس:", reply_markup=course_kb())
        except Exception as e:
            ctx.user_data["step"] = "handle"
            await msg.edit_text(f"الدخول فشل: {e}\n\nابعت الايميل تاني:",
                                reply_markup=ForceReply(selective=True))
        finally:
            await q.close()


async def run_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u, p = ctx.user_data.get("handle"), ctx.user_data.get("password")
    c = ctx.user_data.get("course")
    if not u or not p:
        return await update.message.reply_text("ابعت /start الأول.")
    if not c:
        return await update.message.reply_text("اختار الكورس الأول.")
    if ctx.user_data.get("busy"):
        return await update.message.reply_text("فيه شغل شغال.")

    nums = [x for x in (ctx.args or []) if x.isdigit()]
    if len(nums) >= 2:
        lo, hi = int(nums[0]), int(nums[1])
    else:
        lo, hi = 1, int(os.getenv("MAX_LEVEL", "42"))
    if lo < 1 or hi < lo:
        return await update.message.reply_text("مدى غلط.")

    ctx.user_data["busy"] = True
    try:
        await runner.run(update, c, list(range(lo, hi + 1)), (u, p))
        await update.message.reply_text(f"خلص {lo}-{hi}.")
    except Exception as e:
        logging.exception("run failed")
        await update.message.reply_text(f"وقفت بخطأ: {e}")
    finally:
        ctx.user_data["busy"] = False


def main():
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_all))
    app.add_handler(CallbackQueryHandler(pick_course, pattern="^crs:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()