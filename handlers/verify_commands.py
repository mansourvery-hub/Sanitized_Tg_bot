"""验证命令处理器"""
import asyncio
import logging
import time

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from Boltnew.sheerid_verifier import SheerIDVerifier as BoltnewVerifier
from config import VERIFY_COST
from database_mysql import Database
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from utils.messages import (
    get_insufficient_balance_message,
    get_user_lang,
    get_verify_usage_message,
    t,
)
from youtube.sheerid_verifier import SheerIDVerifier as YouTubeVerifier

# 尝试导入并发控制，如果失败则使用空实现
try:
    from utils.concurrency import get_verification_semaphore
except ImportError:
    # 如果导入失败，创建一个简单的实现
    def get_verification_semaphore(verification_type: str):
        return asyncio.Semaphore(3)

logger = logging.getLogger(__name__)


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /verify 命令 - Gemini One Pro"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify", "Gemini One Pro", lang=lang)
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"], lang=lang)
        )
        return

    verification_id = OneVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text(t("invalid_link", lang=lang))
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text(t("deduct_failed", lang=lang))
        return

    if lang == "zh":
        start_text = (
            f"开始处理 Gemini One Pro 认证...\n"
            f"验证ID: {verification_id}\n"
            f"已扣除 {VERIFY_COST} 积分\n\n"
            "请稍候，这可能需要 1-2 分钟..."
        )
    else:
        start_text = (
            f"Processing Gemini One Pro verification...\n"
            f"Verification ID: {verification_id}\n"
            f"Deducted {VERIFY_COST} point(s)\n\n"
            "Please wait, this may take 1-2 minutes..."
        )

    processing_msg = await update.message.reply_text(start_text)

    try:
        verifier = OneVerifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "gemini_one_pro",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            if lang == "zh":
                result_msg = "✅ 认证成功！\n\n"
                if result.get("pending"):
                    result_msg += "文档已提交，等待人工审核。\n"
                if result.get("redirect_url"):
                    result_msg += f"跳转链接：\n{result['redirect_url']}"
            else:
                result_msg = "✅ Verification Successful!\n\n"
                if result.get("pending"):
                    result_msg += "Document submitted, pending manual review.\n"
                if result.get("redirect_url"):
                    result_msg += f"Redirect URL:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            err_reason = result.get('message', 'Unknown error')
            if lang == "zh":
                fail_text = f"❌ 认证失败：{err_reason}\n\n已退回 {VERIFY_COST} 积分"
            else:
                fail_text = f"❌ Verification Failed: {err_reason}\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(fail_text)
    except Exception as e:
        logger.error("验证过程出错: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        if lang == "zh":
            err_msg = f"❌ 处理过程中出现错误，请稍后重试。\n\n已退回 {VERIFY_COST} 积分"
        else:
            err_msg = f"❌ An error occurred during processing. Please try again later.\n\nRefunded {VERIFY_COST} point(s)"
        await processing_msg.edit_text(err_msg)


async def verify2_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /verify2 命令 - ChatGPT Teacher K12"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify2", "ChatGPT Teacher K12", lang=lang)
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"], lang=lang)
        )
        return

    verification_id = K12Verifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text(t("invalid_link", lang=lang))
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text(t("deduct_failed", lang=lang))
        return

    if lang == "zh":
        start_text = (
            f"开始处理 ChatGPT Teacher K12 认证...\n"
            f"验证ID: {verification_id}\n"
            f"已扣除 {VERIFY_COST} 积分\n\n"
            "请稍候，这可能需要 1-2 分钟..."
        )
    else:
        start_text = (
            f"Processing ChatGPT Teacher K12 verification...\n"
            f"Verification ID: {verification_id}\n"
            f"Deducted {VERIFY_COST} point(s)\n\n"
            "Please wait, this may take 1-2 minutes..."
        )

    processing_msg = await update.message.reply_text(start_text)

    try:
        verifier = K12Verifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "chatgpt_teacher_k12",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            if lang == "zh":
                result_msg = "✅ 认证成功！\n\n"
                if result.get("pending"):
                    result_msg += "文档已提交，等待人工审核。\n"
                if result.get("redirect_url"):
                    result_msg += f"跳转链接：\n{result['redirect_url']}"
            else:
                result_msg = "✅ Verification Successful!\n\n"
                if result.get("pending"):
                    result_msg += "Document submitted, pending manual review.\n"
                if result.get("redirect_url"):
                    result_msg += f"Redirect URL:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            err_reason = result.get('message', 'Unknown error')
            if lang == "zh":
                fail_text = f"❌ 认证失败：{err_reason}\n\n已退回 {VERIFY_COST} 积分"
            else:
                fail_text = f"❌ Verification Failed: {err_reason}\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(fail_text)
    except Exception as e:
        logger.error("验证过程出错: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        if lang == "zh":
            err_msg = f"❌ 处理过程中出现错误，请稍后重试。\n\n已退回 {VERIFY_COST} 积分"
        else:
            err_msg = f"❌ An error occurred during processing. Please try again later.\n\nRefunded {VERIFY_COST} point(s)"
        await processing_msg.edit_text(err_msg)


async def verify3_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /verify3 命令 - Spotify Student"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify3", "Spotify Student", lang=lang)
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"], lang=lang)
        )
        return

    verification_id = SpotifyVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text(t("invalid_link", lang=lang))
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text(t("deduct_failed", lang=lang))
        return

    if lang == "zh":
        start_text = (
            f"开始处理 Spotify Student 认证...\n"
            f"验证ID: {verification_id}\n"
            f"已扣除 {VERIFY_COST} 积分\n\n"
            "请稍候，这可能需要 1-2 分钟..."
        )
    else:
        start_text = (
            f"Processing Spotify Student verification...\n"
            f"Verification ID: {verification_id}\n"
            f"Deducted {VERIFY_COST} point(s)\n\n"
            "Please wait, this may take 1-2 minutes..."
        )

    processing_msg = await update.message.reply_text(start_text)

    try:
        verifier = SpotifyVerifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "spotify_student",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            if lang == "zh":
                result_msg = "✅ 认证成功！\n\n"
                if result.get("pending"):
                    result_msg += "文档已提交，等待人工审核。\n"
                if result.get("redirect_url"):
                    result_msg += f"跳转链接：\n{result['redirect_url']}"
            else:
                result_msg = "✅ Verification Successful!\n\n"
                if result.get("pending"):
                    result_msg += "Document submitted, pending manual review.\n"
                if result.get("redirect_url"):
                    result_msg += f"Redirect URL:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            err_reason = result.get('message', 'Unknown error')
            if lang == "zh":
                fail_text = f"❌ 认证失败：{err_reason}\n\n已退回 {VERIFY_COST} 积分"
            else:
                fail_text = f"❌ Verification Failed: {err_reason}\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(fail_text)
    except Exception as e:
        logger.error("验证过程出错: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        if lang == "zh":
            err_msg = f"❌ 处理过程中出现错误，请稍后重试。\n\n已退回 {VERIFY_COST} 积分"
        else:
            err_msg = f"❌ An error occurred during processing. Please try again later.\n\nRefunded {VERIFY_COST} point(s)"
        await processing_msg.edit_text(err_msg)


async def verify4_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /verify4 命令 - Bolt.new Teacher"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify4", "Bolt.new Teacher", lang=lang)
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"], lang=lang)
        )
        return

    verification_id = BoltnewVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text(t("invalid_link", lang=lang))
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text(t("deduct_failed", lang=lang))
        return

    if lang == "zh":
        start_text = (
            f"🚀 开始处理 Bolt.new Teacher 认证...\n"
            f"已扣除 {VERIFY_COST} 积分\n\n"
            "📤 正在提交文档..."
        )
    else:
        start_text = (
            f"🚀 Processing Bolt.new Teacher verification...\n"
            f"Deducted {VERIFY_COST} point(s)\n\n"
            "📤 Submitting documents..."
        )

    processing_msg = await update.message.reply_text(start_text)

    # 使用信号量控制并发
    semaphore = get_verification_semaphore("bolt_teacher")

    try:
        async with semaphore:
            # 第1步：提交文档
            verifier = BoltnewVerifier(url, verification_id=verification_id)
            result = await asyncio.to_thread(verifier.verify)

        if not result.get("success"):
            # 提交失败，退款
            db.add_balance(user_id, VERIFY_COST)
            err_reason = result.get('message', 'Unknown error')
            if lang == "zh":
                fail_text = f"❌ 文档提交失败：{err_reason}\n\n已退回 {VERIFY_COST} 积分"
            else:
                fail_text = f"❌ Document submission failed: {err_reason}\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(fail_text)
            return

        vid = result.get("verification_id", "")
        if not vid:
            db.add_balance(user_id, VERIFY_COST)
            if lang == "zh":
                no_vid_text = f"❌ 未获取到验证ID\n\n已退回 {VERIFY_COST} 积分"
            else:
                no_vid_text = f"❌ Failed to get verification ID\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(no_vid_text)
            return

        # 更新消息
        if lang == "zh":
            update_text = (
                f"✅ 文档已提交！\n"
                f"📋 验证ID: `{vid}`\n\n"
                f"🔍 正在自动获取认证码...\n"
                f"（最多等待20秒）"
            )
        else:
            update_text = (
                f"✅ Document submitted!\n"
                f"📋 Verification ID: `{vid}`\n\n"
                f"🔍 Automatically fetching reward code...\n"
                f"(Waiting up to 20 seconds)"
            )
        await processing_msg.edit_text(update_text)

        # 第2步：自动获取认证码（最多20秒）
        code = await _auto_get_reward_code(vid, max_wait=20, interval=5)

        if code:
            if lang == "zh":
                result_msg = (
                    f"🎉 认证成功！\n\n"
                    f"✅ 文档已提交\n"
                    f"✅ 审核已通过\n"
                    f"🔑 认证码: `{code}`\n\n"
                    f"💡 请在 Bolt.new 中输入此认证码完成认证"
                )
            else:
                result_msg = (
                    f"🎉 Verification Successful!\n\n"
                    f"✅ Document submitted\n"
                    f"✅ Approved\n"
                    f"🔑 Reward Code: `{code}`\n\n"
                    f"💡 Please enter this code in Bolt.new to complete verification."
                )
            status = "success"
        else:
            if lang == "zh":
                result_msg = (
                    f"⏳ 文档已提交，等待审核中...\n\n"
                    f"📋 验证ID: `{vid}`\n\n"
                    f"💡 审核通常需要 1-5 分钟。\n"
                    f"审核完成后，使用以下命令获取认证码：\n"
                    f"`/getV4Code {vid}`\n\n"
                    f"（点击上方命令可直接复制）"
                )
            else:
                result_msg = (
                    f"⏳ Document submitted, awaiting review...\n\n"
                    f"📋 Verification ID: `{vid}`\n\n"
                    f"💡 Review usually takes 1-5 minutes.\n"
                    f"Once approved, retrieve your code using:\n"
                    f"`/getV4Code {vid}`"
                )
            status = "pending"

        db.add_verification(
            user_id,
            "bolt_teacher",
            url,
            status,
            f"verification_id: {vid}, code: {code}" if code else f"verification_id: {vid}",
        )

        await processing_msg.edit_text(result_msg)

    except Exception as e:
        logger.error("Bolt.new 验证过程出错: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        if lang == "zh":
            err_msg = f"❌ 处理过程中出现错误，请稍后重试。\n\n已退回 {VERIFY_COST} 积分"
        else:
            err_msg = f"❌ An error occurred during processing. Please try again later.\n\nRefunded {VERIFY_COST} point(s)"
        await processing_msg.edit_text(err_msg)


async def _auto_get_reward_code(verification_id: str, max_wait: int = 20, interval: int = 5) -> str | None:
    """后台自动轮询获取认证码"""
    start_time = time.time()
    url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < max_wait:
            await asyncio.sleep(interval)

            try:
                response = await client.get(url, timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    current_step = data.get("currentStep")

                    if current_step == "success":
                        reward_code = data.get("rewardCode")
                        if reward_code:
                            elapsed = int(time.time() - start_time)
                            logger.info(f"✅ 自动获取code成功: {reward_code} (耗时{elapsed}秒)")
                            return reward_code

                    elif current_step == "error":
                        logger.warning(f"审核失败: {data.get('errorIds', [])}")
                        return None

            except Exception as e:
                logger.warning(f"查询认证码出错: {e}")
                continue

    elapsed = int(time.time() - start_time)
    logger.info(f"自动获取code超时({elapsed}秒)，让用户手动查询")
    return None


async def verify5_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /verify5 命令 - YouTube Student Premium"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        await update.message.reply_text(
            get_verify_usage_message("/verify5", "YouTube Student Premium", lang=lang)
        )
        return

    url = context.args[0]
    user = db.get_user(user_id)
    if user["balance"] < VERIFY_COST:
        await update.message.reply_text(
            get_insufficient_balance_message(user["balance"], lang=lang)
        )
        return

    verification_id = YouTubeVerifier.parse_verification_id(url)
    if not verification_id:
        await update.message.reply_text(t("invalid_link", lang=lang))
        return

    if not db.deduct_balance(user_id, VERIFY_COST):
        await update.message.reply_text(t("deduct_failed", lang=lang))
        return

    if lang == "zh":
        start_text = (
            f"开始处理 YouTube Student Premium 认证...\n"
            f"验证ID: {verification_id}\n"
            f"已扣除 {VERIFY_COST} 积分\n\n"
            "请稍候，这可能需要 1-2 分钟..."
        )
    else:
        start_text = (
            f"Processing YouTube Student Premium verification...\n"
            f"Verification ID: {verification_id}\n"
            f"Deducted {VERIFY_COST} point(s)\n\n"
            "Please wait, this may take 1-2 minutes..."
        )

    processing_msg = await update.message.reply_text(start_text)

    try:
        verifier = YouTubeVerifier(verification_id)
        result = await asyncio.to_thread(verifier.verify)

        db.add_verification(
            user_id,
            "youtube_student_premium",
            url,
            "success" if result["success"] else "failed",
            str(result),
        )

        if result["success"]:
            if lang == "zh":
                result_msg = "✅ 认证成功！\n\n"
                if result.get("pending"):
                    result_msg += "文档已提交，等待人工审核。\n"
                if result.get("redirect_url"):
                    result_msg += f"跳转链接：\n{result['redirect_url']}"
            else:
                result_msg = "✅ Verification Successful!\n\n"
                if result.get("pending"):
                    result_msg += "Document submitted, pending manual review.\n"
                if result.get("redirect_url"):
                    result_msg += f"Redirect URL:\n{result['redirect_url']}"
            await processing_msg.edit_text(result_msg)
        else:
            db.add_balance(user_id, VERIFY_COST)
            err_reason = result.get('message', 'Unknown error')
            if lang == "zh":
                fail_text = f"❌ 认证失败：{err_reason}\n\n已退回 {VERIFY_COST} 积分"
            else:
                fail_text = f"❌ Verification Failed: {err_reason}\n\nRefunded {VERIFY_COST} point(s)"
            await processing_msg.edit_text(fail_text)
    except Exception as e:
        logger.error("YouTube 验证过程出错: %s", e)
        db.add_balance(user_id, VERIFY_COST)
        if lang == "zh":
            err_msg = f"❌ 处理过程中出现错误，请稍后重试。\n\n已退回 {VERIFY_COST} 积分"
        else:
            err_msg = f"❌ An error occurred during processing. Please try again later.\n\nRefunded {VERIFY_COST} point(s)"
        await processing_msg.edit_text(err_msg)


async def getV4Code_command(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Database):
    """处理 /getV4Code 命令 - 获取 Bolt.new 认证码"""
    user_id = update.effective_user.id
    lang = get_user_lang(db, user_id)

    if db.is_user_blocked(user_id):
        await update.message.reply_text(t("user_blocked", lang=lang))
        return

    if not db.user_exists(user_id):
        await update.message.reply_text(t("not_registered", lang=lang))
        return

    if not context.args:
        if lang == "zh":
            usage_msg = (
                "使用方法: /getV4Code <verification_id>\n\n"
                "示例:\n"
                "/getV4Code 674a1b2c3d4e5f6a7b8c9d0e\n\n"
                "提示: verification_id 是在提交 /verify4 时返回的验证ID"
            )
        else:
            usage_msg = (
                "Usage: /getV4Code <verification_id>\n\n"
                "Example:\n"
                "/getV4Code 674a1b2c3d4e5f6a7b8c9d0e\n\n"
                "Note: The verification_id is returned when you submit /verify4."
            )
        await update.message.reply_text(usage_msg)
        return

    verification_id = context.args[0].strip()

    if lang == "zh":
        query_msg = f"🔍 正在查询验证状态...\nID: `{verification_id}`"
    else:
        query_msg = f"🔍 Querying verification status...\nID: `{verification_id}`"
    processing_msg = await update.message.reply_text(query_msg)

    try:
        url = f"https://services.sheerid.com/rest/v2/verification/{verification_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

        if response.status_code != 200:
            if lang == "zh":
                fail_msg = f"❌ 查询失败 (状态码: {response.status_code})\n\n请检查 verification_id 是否正确。"
            else:
                fail_msg = f"❌ Query failed (status code: {response.status_code})\n\nPlease check if verification_id is correct."
            await processing_msg.edit_text(fail_msg)
            return

        data = response.json()
        current_step = data.get("currentStep")

        if current_step == "success":
            code = data.get("rewardCode", "未找到认证码")
            if lang == "zh":
                result_msg = (
                    f"🎉 认证成功！\n\n"
                    f"🔑 认证码: `{code}`\n\n"
                    f"💡 请在 Bolt.new 中输入此认证码完成认证"
                )
            else:
                result_msg = (
                    f"🎉 Verification Successful!\n\n"
                    f"🔑 Reward Code: `{code}`\n\n"
                    f"💡 Please enter this code in Bolt.new to complete verification."
                )
        elif current_step == "pending":
            if lang == "zh":
                result_msg = (
                    f"⏳ 审核中...\n\n"
                    f"文档已提交，正在等待人工审核。\n"
                    f"请稍后再试: `/getV4Code {verification_id}`"
                )
            else:
                result_msg = (
                    f"⏳ Pending review...\n\n"
                    f"Document submitted, awaiting review.\n"
                    f"Check again shortly: `/getV4Code {verification_id}`"
                )
        elif current_step == "error":
            error_ids = data.get("errorIds", ["未知错误"])
            if lang == "zh":
                result_msg = (
                    f"❌ 审核未通过\n\n"
                    f"原因: {', '.join(error_ids)}\n\n"
                    f"建议重新使用 /verify4 提交认证"
                )
            else:
                result_msg = (
                    f"❌ Verification Not Approved\n\n"
                    f"Reason: {', '.join(error_ids)}\n\n"
                    f"Please submit again using /verify4"
                )
        else:
            if lang == "zh":
                result_msg = (
                    f"ℹ️ 当前状态: {current_step}\n\n"
                    f"尚未完成审核，请稍后再试。\n"
                    f"`/getV4Code {verification_id}`"
                )
            else:
                result_msg = (
                    f"ℹ️ Current status: {current_step}\n\n"
                    f"Review not complete yet. Check again shortly:\n"
                    f"`/getV4Code {verification_id}`"
                )

        await processing_msg.edit_text(result_msg)

    except Exception as e:
        logger.error("获取 Bolt.new 认证码失败: %s", e)
        if lang == "zh":
            err_msg = f"❌ 查询出错: {e!s}\n\n请稍后重试。"
        else:
            err_msg = f"❌ Query error: {e!s}\n\nPlease try again later."
        await processing_msg.edit_text(err_msg)
