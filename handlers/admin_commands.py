"""管理员命令处理器"""
import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_USER_ID
from database_mysql import Database
from utils.checks import reject_group_command
from utils.messages import get_text, get_user_lang

logger = logging.getLogger(__name__)


async def addbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /addbalance 命令 - 管理员增加积分"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(get_text("admin_addbalance_usage", lang=lang))
        return

    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])

        if not db.user_exists(target_user_id):
            await update.message.reply_text(get_text("admin_user_not_found", lang=lang))
            return

        if db.add_balance(target_user_id, amount):
            user = db.get_user(target_user_id)
            if lang == "zh":
                msg = f"✅ 成功为用户 {target_user_id} 增加 {amount} 积分。\n当前积分：{user['balance']}"
            else:
                msg = f"✅ Successfully added {amount} points to user {target_user_id}.\nCurrent balance: {user['balance']}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(get_text("operation_failed", lang=lang))
    except ValueError:
        if lang == "zh":
            await update.message.reply_text("参数格式错误，请输入有效的数字。")
        else:
            await update.message.reply_text("Invalid argument format. Please provide valid numbers.")


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /block 命令 - 管理员拉黑用户"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    if not context.args:
        if lang == "zh":
            await update.message.reply_text("使用方法: /block <用户ID>\n\n示例: /block 123456789")
        else:
            await update.message.reply_text("Usage: /block <user_id>\n\nExample: /block 123456789")
        return

    try:
        target_user_id = int(context.args[0])

        if not db.user_exists(target_user_id):
            await update.message.reply_text(get_text("admin_user_not_found", lang=lang))
            return

        if db.block_user(target_user_id):
            if lang == "zh":
                await update.message.reply_text(f"✅ 已拉黑用户 {target_user_id}。")
            else:
                await update.message.reply_text(f"✅ User {target_user_id} has been blocked.")
        else:
            await update.message.reply_text(get_text("operation_failed", lang=lang))
    except ValueError:
        if lang == "zh":
            await update.message.reply_text("参数格式错误，请输入有效的用户ID。")
        else:
            await update.message.reply_text("Invalid argument format. Please provide a valid user ID.")


async def white_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /white 命令 - 管理员取消拉黑"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    if not context.args:
        if lang == "zh":
            await update.message.reply_text("使用方法: /white <用户ID>\n\n示例: /white 123456789")
        else:
            await update.message.reply_text("Usage: /white <user_id>\n\nExample: /white 123456789")
        return

    try:
        target_user_id = int(context.args[0])

        if not db.user_exists(target_user_id):
            await update.message.reply_text(get_text("admin_user_not_found", lang=lang))
            return

        if db.unblock_user(target_user_id):
            if lang == "zh":
                await update.message.reply_text(f"✅ 已解除用户 {target_user_id} 的拉黑状态。")
            else:
                await update.message.reply_text(f"✅ User {target_user_id} has been unblocked.")
        else:
            await update.message.reply_text(get_text("operation_failed", lang=lang))
    except ValueError:
        if lang == "zh":
            await update.message.reply_text("参数格式错误，请输入有效的用户ID。")
        else:
            await update.message.reply_text("Invalid argument format. Please provide a valid user ID.")


async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /blacklist 命令 - 管理员查看黑名单"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    blacklist = db.get_blacklist()

    if not blacklist:
        if lang == "zh":
            await update.message.reply_text("📋 黑名单为空。")
        else:
            await update.message.reply_text("📋 Blacklist is empty.")
        return

    if lang == "zh":
        msg = f"📋 黑名单列表 (共 {len(blacklist)} 人):\n\n"
        for user in blacklist:
            username = f"@{user['username']}" if user['username'] else "无用户名"
            msg += f"• `{user['user_id']}` - {user['full_name']} ({username})\n"
    else:
        msg = f"📋 Blacklist ({len(blacklist)} users):\n\n"
        for user in blacklist:
            username = f"@{user['username']}" if user['username'] else "No username"
            msg += f"• `{user['user_id']}` - {user['full_name']} ({username})\n"

    await update.message.reply_text(msg)


async def genkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /genkey 命令 - 管理员生成卡密"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    if not context.args or len(context.args) < 2:
        if lang == "zh":
            await update.message.reply_text(
                "使用方法: /genkey <卡密> <积分> [可用次数] [有效天数]\n\n"
                "参数说明:\n"
                "• 卡密: 自定义卡密码\n"
                "• 积分: 兑换可获得的积分数\n"
                "• 可用次数: 可被多少人使用（默认1次）\n"
                "• 有效天数: 多少天后过期（默认30天）\n\n"
                "示例:\n"
                "/genkey VIP2024 10\n"
                "/genkey PROMO100 5 100 7"
            )
        else:
            await update.message.reply_text(
                "Usage: /genkey <key> <points> [max_uses] [valid_days]\n\n"
                "Parameters:\n"
                "• key: Custom code text\n"
                "• points: Points granted upon redemption\n"
                "• max_uses: Maximum redemptions (default: 1)\n"
                "• valid_days: Validity duration in days (default: 30)\n\n"
                "Example:\n"
                "/genkey VIP2024 10\n"
                "/genkey PROMO100 5 100 7"
            )
        return

    try:
        key_code = context.args[0]
        points = int(context.args[1])
        max_uses = int(context.args[2]) if len(context.args) > 2 else 1
        valid_days = int(context.args[3]) if len(context.args) > 3 else 30

        if points <= 0:
            if lang == "zh":
                await update.message.reply_text("积分数量必须大于 0。")
            else:
                await update.message.reply_text("Points must be greater than 0.")
            return

        if max_uses <= 0:
            if lang == "zh":
                await update.message.reply_text("可用次数必须大于 0。")
            else:
                await update.message.reply_text("Max uses must be greater than 0.")
            return

        if valid_days <= 0:
            if lang == "zh":
                await update.message.reply_text("有效天数必须大于 0。")
            else:
                await update.message.reply_text("Valid days must be greater than 0.")
            return

        if db.create_card_key(key_code, points, max_uses, valid_days):
            if lang == "zh":
                msg = (
                    f"✅ 卡密生成成功！\n\n"
                    f"🔑 卡密: `{key_code}`\n"
                    f"💰 积分: {points}\n"
                    f"👥 可用次数: {max_uses}\n"
                    f"⏱ 有效天数: {valid_days} 天\n\n"
                    f"兑换命令: `/use {key_code}`"
                )
            else:
                msg = (
                    f"✅ Card key generated successfully!\n\n"
                    f"🔑 Key: `{key_code}`\n"
                    f"💰 Points: {points}\n"
                    f"👥 Max uses: {max_uses}\n"
                    f"⏱ Valid days: {valid_days} days\n\n"
                    f"Redemption command: `/use {key_code}`"
                )
            await update.message.reply_text(msg)
        else:
            if lang == "zh":
                await update.message.reply_text("卡密已存在或创建失败。")
            else:
                await update.message.reply_text("Card key already exists or creation failed.")
    except ValueError:
        if lang == "zh":
            await update.message.reply_text("参数格式错误，请输入有效的数字。")
        else:
            await update.message.reply_text("Invalid parameter format. Please enter valid numbers.")


async def listkeys_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /listkeys 命令 - 管理员查看卡密列表"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    keys = db.get_active_card_keys()

    if not keys:
        if lang == "zh":
            await update.message.reply_text("📋 暂无有效卡密。")
        else:
            await update.message.reply_text("📋 No active card keys.")
        return

    if lang == "zh":
        msg = f"📋 有效卡密列表 (共 {len(keys)} 个):\n\n"
        for key in keys:
            status = "✅ 有效" if key['is_active'] else "❌ 禁用"
            expires_at = key['expires_at'].strftime('%Y-%m-%d %H:%M') if key.get('expires_at') else "永久"
            msg += (
                f"• `{key['key_code']}` ({status})\n"
                f"  积分: +{key['points']} | 使用: {key['used_count']}/{key['max_uses']} | 过期: {expires_at}\n\n"
            )
    else:
        msg = f"📋 Active Card Keys ({len(keys)} items):\n\n"
        for key in keys:
            status = "✅ Active" if key['is_active'] else "❌ Disabled"
            expires_at = key['expires_at'].strftime('%Y-%m-%d %H:%M') if key.get('expires_at') else "Never"
            msg += (
                f"• `{key['key_code']}` ({status})\n"
                f"  Points: +{key['points']} | Uses: {key['used_count']}/{key['max_uses']} | Expires: {expires_at}\n\n"
            )

    await update.message.reply_text(msg)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /broadcast 命令 - 管理员群发通知"""
    if await reject_group_command(update):
        return

    user_id = update.effective_user.id
    lang = get_user_lang(user_id, db)

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(get_text("admin_no_permission", lang=lang))
        return

    if not context.args:
        if lang == "zh":
            await update.message.reply_text("使用方法: /broadcast <通知内容>")
        else:
            await update.message.reply_text("Usage: /broadcast <message>")
        return

    broadcast_text = " ".join(context.args)

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
        users = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not users:
        if lang == "zh":
            await update.message.reply_text("没有找到可接收通知的用户。")
        else:
            await update.message.reply_text("No active users found.")
        return

    total = len(users)
    if lang == "zh":
        progress_msg = await update.message.reply_text(f"📢 开始向 {total} 位用户群发通知...")
    else:
        progress_msg = await update.message.reply_text(f"📢 Starting broadcast to {total} users...")

    success = 0
    failed = 0

    for row in users:
        uid = row[0]
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 **系统通知 / Announcement**\n\n{broadcast_text}",
                parse_mode="Markdown",
            )
            success += 1
            await asyncio.sleep(0.05)  # 避免触发 Telegram 发送频率限制
        except Exception as e:
            failed += 1
            logger.warning("广播到 %s 失败: %s", uid, e)

    if lang == "zh":
        await progress_msg.edit_text(
            f"📢 群发完成！\n\n"
            f"• 总用户数: {total}\n"
            f"• 发送成功: {success}\n"
            f"• 发送失败: {failed}"
        )
    else:
        await progress_msg.edit_text(
            f"📢 Broadcast finished!\n\n"
            f"• Total recipients: {total}\n"
            f"• Succeeded: {success}\n"
            f"• Failed: {failed}"
        )
