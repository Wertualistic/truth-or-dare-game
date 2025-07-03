import random
import os
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.orm import declarative_base, sessionmaker

# ==================== Setup ====================
token = os.getenv("BOT_TOKEN")
Base = declarative_base()

class Truth(Base):
    __tablename__ = 'truths'
    id = Column(Integer, primary_key=True)
    question = Column(String)

class Dare(Base):
    __tablename__ = 'dares'
    id = Column(Integer, primary_key=True)
    challenge = Column(String, nullable=True)
    file_id = Column(String, nullable=True)
    caption = Column(String, nullable=True)

engine = create_engine('sqlite:///truthordare.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==================== Helpers ====================
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private":
        return True
    user_id = update.effective_user.id
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    return any(admin.user.id == user_id for admin in admins)


def is_private_owner(update: Update):
    return update.effective_chat.type == "private" and update.effective_user.username == "coderaliy"

# ==================== Commands ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to Truth or Dare bot!\nUse /truthordare to start playing.")

async def add_truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only admins can add Truth questions.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addtruth <your truth question>")
        return
    session = Session()
    session.add(Truth(question=" ".join(context.args)))
    session.commit()
    session.close()
    await update.message.reply_text("✅ Truth added!")

async def add_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only admins can add Dares.")
        return

    session = Session()
    message = update.message

    if message.photo:
        photo = message.photo[-1]
        file_id = photo.file_id
        caption = message.caption.replace("/adddare", "").strip() if message.caption else ""
        session.add(Dare(file_id=file_id, caption=caption))
        await message.reply_text("📸 Image Dare added!")
    elif context.args:
        text = " ".join(context.args)
        session.add(Dare(challenge=text))
        await message.reply_text("✅ Text Dare added!")
    else:
        await message.reply_text("❌ Please send a photo or text with: /adddare <challenge>")
        session.close()
        return

    session.commit()
    session.close()

async def truth_or_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = random.choice(["truth", "dare"])
    if choice == "truth":
        text = "🎲 You got *Truth*!\nTo get your question, send: /gettruth"
    else:
        text = "🎲 You got *Dare*!\nTo get your challenge, send: /getdare"
    await update.message.reply_text(text, parse_mode='Markdown')

async def get_truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    truth = session.query(Truth).order_by(func.random()).first()
    session.close()
    if truth:
        await update.message.reply_text(f"🟢 *Truth*: {truth.question}", parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ No truths available yet. Admins can add them using /addtruth")

async def get_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    dare = session.query(Dare).order_by(func.random()).first()
    session.close()
    if not dare:
        await update.message.reply_text("⚠️ No dares available.")
        return
    if dare.file_id:
        await update.message.reply_photo(photo=dare.file_id, caption=dare.caption or "🟥 Your dare!")
    else:
        await update.message.reply_text(f"🔴 Dare: {dare.challenge}")

async def list_truths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only admins can list truths.")
        return
    session = Session()
    truths = session.query(Truth).all()
    session.close()
    if not truths:
        await update.message.reply_text("📭 No truths found.")
        return
    text = "\n".join([f"{t.id}. {t.question}" for t in truths])
    await update.message.reply_text(f"📘 Truths:\n{text}")

async def list_dares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only admins can list dares.")
        return
    session = Session()
    dares = session.query(Dare).all()
    session.close()
    text = ""
    for d in dares:
        if d.challenge:
            text += f"{d.id}. {d.challenge}\n"
        elif d.caption:
            text += f"{d.id}. [Image Dare] {d.caption}\n"
        else:
            text += f"{d.id}. [Image Dare]\n"
    await update.message.reply_text(f"📕 Dares:\n{text}")

async def delete_truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_owner(update) and not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only @coderaliy or group admins can delete truths.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /deletetruth <id>")
        return
    try:
        id_to_delete = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return
    session = Session()
    truth = session.query(Truth).filter_by(id=id_to_delete).first()
    if not truth:
        await update.message.reply_text("❌ Truth not found.")
    else:
        session.delete(truth)
        session.commit()
        await update.message.reply_text(f"✅ Truth #{id_to_delete} deleted.")
    session.close()

async def delete_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_owner(update) and not await is_user_admin(update, context):
        await update.message.reply_text("❌ Only @coderaliy or group admins can delete dares.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /deletedare <id>")
        return
    try:
        id_to_delete = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return
    session = Session()
    dare = session.query(Dare).filter_by(id=id_to_delete).first()
    if not dare:
        await update.message.reply_text("❌ Dare not found.")
    else:
        session.delete(dare)
        session.commit()
        await update.message.reply_text(f"✅ Dare #{id_to_delete} deleted.")
    session.close()

async def set_bot_commands(app):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("truthordare", "Start a random truth or dare"),
        BotCommand("gettruth", "Get a random truth"),
        BotCommand("getdare", "Get a random dare"),
        BotCommand("addtruth", "Add a truth (admins only)"),
        BotCommand("adddare", "Add a dare (admins only)"),
        BotCommand("listtruths", "List all truths (admins only)"),
        BotCommand("listdares", "List all dares (admins only)"),
        BotCommand("deletetruth", "Delete a truth by ID (admins only)"),
        BotCommand("deletedare", "Delete a dare by ID (admins only)")
    ]
    await app.bot.set_my_commands(commands)

# ==================== Runner ====================
if __name__ == "__main__":
    async def main():
        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("addtruth", add_truth))
        app.add_handler(CommandHandler("adddare", add_dare))
        app.add_handler(CommandHandler("truthordare", truth_or_dare))
        app.add_handler(CommandHandler("gettruth", get_truth))
        app.add_handler(CommandHandler("getdare", get_dare))
        app.add_handler(CommandHandler("listtruths", list_truths))
        app.add_handler(CommandHandler("listdares", list_dares))
        app.add_handler(CommandHandler("deletetruth", delete_truth))
        app.add_handler(CommandHandler("deletedare", delete_dare))

        app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex("^/adddare"), add_dare))

        await set_bot_commands(app)

        print("🤖 Bot is running...")
        await app.run_polling()

    import asyncio
    asyncio.run(main())
