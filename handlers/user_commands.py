"""用户命令处理器 (支持多语言 English / 中文)"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command
from utils.messages import (
    get_about_message,
    get_help_message,
    get_text,
    get_user_lang,
    get_welcome_message,
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /start 命令"""
    if await reject_group_command(update):
        return

    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    full_name = user.full_name or ""
    lang = get_user_lang(db, user_id)

    # 已初始化直接返回
    if db.user_exists(user_id):
        await update.message.reply_text(
            get_text("welcome_back", lang, full_name=full_name)
        )
        return

    # 邀请参与
    invited_by: int | None = None
    if context.args:
        try:
            invited_by = int(context.args[0])
            if not db.user_exists(invited_by):
                invited_by = None
        except Exception:
            invited_by = None

    # 创建用户
    if db.create_user(user_id, username, full_name, invited_by):
        welcome_msg = get_welcome_message(full_name, bool(invited_by), lang=lang)
        await update.message.reply_text(welcome_msg)
    else:
        await update.message.reply_text(get_text("register_failed", lang))


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /about 命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)
    await update.message.reply_text(get_about_message(lang=lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /help 命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_USER_ID
    lang = get_user_lang(db, user_id)
    await update.message.reply_text(get_help_message(is_admin, lang=lang))


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /balance 命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(get_text("user_blocked", lang))
        return

    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    await update.message.reply_text(
        get_text("balance_info", lang, balance=user["balance"])
    )


async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /qd 签到命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(get_text("user_blocked", lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # 第1层检查：在命令处理器层面检查
    if not db.can_checkin(user_id):
        await update.message.reply_text(get_text("checkin_already", lang))
        return

    # 第2层检查：在数据库层面执行（SQL原子操作）
    if db.checkin(user_id):
        user = db.get_user(user_id)
        await update.message.reply_text(
            get_text("checkin_success", lang, balance=user["balance"])
        )
    else:
        await update.message.reply_text(get_text("checkin_already", lang))


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /invite 邀请命令"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(get_text("user_blocked", lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(get_text("not_registered", lang))
        return

    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
        get_text("invite_info", lang, invite_link=invite_link)
    )


async def use_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /use 命令 - 使用卡密"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(get_text("user_blocked", lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(get_text("not_registered", lang))
        return

    if not context.args:
        await update.message.reply_text(get_text("use_usage", lang))
        return

    key_code = context.args[0].strip()
    success, message, added_balance = db.use_card_key(user_id, key_code)

    if success:
        user = db.get_user(user_id)
        await update.message.reply_text(
            get_text("use_success", lang, points=added_balance, balance=user["balance"])
        )
    else:
        await update.message.reply_text(
            get_text("use_failed", lang, message=message)
        )


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /lang 命令 - 切换显示语言 (English / 中文)"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    current_lang = get_user_lang(db, user_id)

    if not context.args:
        display = "English (en)" if current_lang == "en" else "中文 (zh)"
        await update.message.reply_text(
            get_text("lang_current", current_lang, lang_display=display)
        )
        return

    chosen = context.args[0].strip().lower()
    if chosen in ("en", "english"):
        target_code = "en"
    elif chosen in ("zh", "cn", "chinese", "中文"):
        target_code = "zh"
    else:
        await update.message.reply_text(get_text("lang_invalid", current_lang))
        return

    db.set_user_language(user_id, target_code)
    await update.message.reply_text(get_text("lang_changed", target_code))
