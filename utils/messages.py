"""多语言与国际化支持 (English / 中文)"""

from config import CHANNEL_URL, HELP_NOTION_URL, VERIFY_COST

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "zh"}

TRANSLATIONS = {
    "en": {
        # General & Registration
        "welcome": (
            "🎉 Welcome, {full_name}!\n"
            "You have registered successfully and received 1 point.\n"
            "{invited_note}"
            "\nThis bot automatically verifies SheerID programs.\n\n"
            "Quick Start:\n"
            "/about - About the bot & supported programs\n"
            "/balance - Check your points balance\n"
            "/lang <en|zh> - Change language\n"
            "/help - View full command list\n\n"
            "Earn more points:\n"
            "/qd - Daily check-in (+1 point)\n"
            "/invite - Invite friends (+2 points each)\n"
            f"Official Channel: {CHANNEL_URL}"
        ),
        "welcome_invited": "Thanks for joining via an invite link! Your inviter earned +2 points.\n",
        "welcome_back": (
            "Welcome back, {full_name}!\n"
            "Your account is already active.\n"
            "Send /help to see all available commands, or /lang en to set English."
        ),
        "register_failed": "Registration failed. Please try again later.",
        "not_registered": "Please send /start to register first.",
        "user_blocked": "Your account has been restricted.",
        "insufficient_balance": (
            f"Insufficient points! Verification requires {VERIFY_COST} points, your balance is {{balance}}.\n\n"
            "Ways to earn points:\n"
            "- Daily check-in: /qd\n"
            "- Invite friends: /invite\n"
            "- Redeem code: /use <card_key>"
        ),
        "deduct_failed": "Failed to deduct points. Please try again later.",
        "invalid_link": "Invalid SheerID link. Please check your link and try again.",

        # /about
        "about": (
            "🤖 SheerID Verification Bot\n\n"
            "Features:\n"
            "- Automatic SheerID student/educator verification\n"
            "- Supports Google Gemini One Pro, ChatGPT K-12, Spotify Student, YouTube Student, Bolt.new Teacher\n\n"
            "Earning Points:\n"
            "- Initial Registration: +1 point\n"
            "- Daily Check-in: +1 point\n"
            "- Friend Referral: +2 points/user\n"
            "- Card Key Redemption: /use <key>\n"
            f"- Official Channel: {CHANNEL_URL}\n\n"
            "How to Use:\n"
            "1. Start the verification on your target service and copy the full SheerID URL.\n"
            "2. Send /verify, /verify2, /verify3, /verify4, or /verify5 with the URL.\n"
            "3. Wait for automated verification and status updates.\n\n"
            "Send /help for all commands."
        ),

        # /help
        "help_header": "📖 SheerID Verification Bot - Help Guide\n\nUser Commands:\n",
        "help_user_commands": (
            "/start - Register or display start menu\n"
            "/about - About the bot & services\n"
            "/balance - Check your points balance\n"
            "/lang <en|zh> - Switch language (English / 中文)\n"
            "/qd - Daily check-in (+1 point)\n"
            "/invite - Get personal invite link (+2 points/user)\n"
            "/use <card_key> - Redeem card key for points\n"
            f"/verify <link> [school] - Google Gemini One Pro (-{VERIFY_COST} points)\n"
            f"/verify2 <link> - ChatGPT Teacher K-12 (-{VERIFY_COST} points)\n"
            f"/verify3 <link> [school] - Spotify Student (-{VERIFY_COST} points)\n"
            f"/verify4 <link> [school] - Bolt.new Teacher (-{VERIFY_COST} points)\n"
            f"/verify5 <link> [school] - YouTube Student (-{VERIFY_COST} points)\n"
            "/getV4Code <verification_id> - Query Bolt.new verification code\n"
            "/help - Display this help guide\n"
            f"Need assistance: {HELP_NOTION_URL}\n"
        ),
        "help_admin_commands": (
            "\nAdmin Commands:\n"
            "/addbalance <user_id> <points> - Add points to user\n"
            "/block <user_id> - Block user\n"
            "/white <user_id> - Unblock user\n"
            "/blacklist - View blacklisted users\n"
            "/genkey <key> <points> [max_uses] [valid_days] - Generate card key\n"
            "/listkeys - View all card keys\n"
            "/broadcast <message> - Send broadcast notification to all users\n"
        ),

        # /balance
        "balance_msg": "💰 Points Balance\n\nCurrent balance: {balance} points",

        # /qd checkin
        "checkin_success": "✅ Check-in successful!\nEarned: +1 point\nCurrent balance: {balance} points",
        "checkin_already": "❌ You have already checked in today. Please come back tomorrow.",

        # /invite
        "invite_msg": (
            "🎁 Your exclusive referral link:\n{invite_link}\n\n"
            "You will receive +2 points for every friend who registers using your link."
        ),

        # /use card key
        "use_usage": "Usage: /use <card_key>",
        "key_invalid": "Invalid or expired card key.",
        "key_already_used": "You have already redeemed this card key.",
        "key_success": "✅ Successfully redeemed card key!\nAdded: +{amount} points\nCurrent balance: {balance} points",
        "key_failed": "Failed to redeem card key. Please try again later.",

        # /lang
        "lang_current": "🌐 Current language: {lang_display}\n\nTo change language, send:\n/lang en (English)\n/lang zh (中文)",
        "lang_changed": "✅ Language changed to English successfully.",
        "lang_invalid": "Invalid language. Supported: /lang en (English) or /lang zh (中文)",

        # Verification messages
        "verify_processing": "⏳ Starting verification...\nService: {service}\nID: {vid}\nPlease wait...",
        "verify_success": "🎉 Verification Succeeded!\nService: {service}\nVerification ID: {vid}",
        "verify_failed": "❌ Verification Failed: {reason}\n\nRefunded {cost} points to your account.",
        "verify_usage": (
            "Usage: {command} <SheerID_URL> [school]\n\n"
            "Example:\n"
            "{command} https://services.sheerid.com/verify/xxx/?verificationId=xxx ucla\n\n"
            "Supported schools:\n"
            "• psu (Penn State - Default)\n"
            "• ucla (Univ. of California, Los Angeles)\n"
            "• nyu (New York University)\n"
            "• umich (University of Michigan)\n"
            "• ut_austin (Univ. of Texas at Austin)\n\n"
            "Steps:\n"
            "1. Visit {service_name} verification page\n"
            "2. Start verification and copy the browser URL\n"
            "3. Send {command} <URL> [school] to the bot"
        ),
    },

    "zh": {
        # General & Registration
        "welcome": (
            "🎉 欢迎，{full_name}！\n"
            "您已成功注册，获得 1 积分。\n"
            "{invited_note}"
            "\n本机器人可自动完成 SheerID 认证。\n\n"
            "快速开始：\n"
            "/about - 了解机器人功能\n"
            "/balance - 查看积分余额\n"
            "/lang <en|zh> - 切换语言\n"
            "/help - 查看完整命令列表\n\n"
            "获取更多积分：\n"
            "/qd - 每日签到\n"
            "/invite - 邀请好友\n"
            f"加入频道：{CHANNEL_URL}"
        ),
        "welcome_invited": "感谢通过邀请链接加入，邀请人已获得 2 积分。\n",
        "welcome_back": (
            "欢迎回来，{full_name}！\n"
            "您已经初始化过了。\n"
            "发送 /help 查看可用命令，或发送 /lang en 切换至英文。"
        ),
        "register_failed": "注册失败，请稍后重试。",
        "not_registered": "请先使用 /start 注册。",
        "user_blocked": "您已被拉黑，无法使用此功能。",
        "insufficient_balance": (
            f"积分不足！需要 {VERIFY_COST} 积分，当前 {{balance}} 积分。\n\n"
            "获取积分方式:\n"
            "- 每日签到 /qd\n"
            "- 邀请好友 /invite\n"
            "- 使用卡密 /use <卡密>"
        ),
        "deduct_failed": "扣除积分失败，请稍后重试。",
        "invalid_link": "无效的 SheerID 链接，请检查后重试。",

        # /about
        "about": (
            "🤖 SheerID 自动认证机器人\n\n"
            "功能介绍:\n"
            "- 自动完成 SheerID 学生/教师认证\n"
            "- 支持 Gemini One Pro、ChatGPT Teacher K12、Spotify Student、YouTube Student、Bolt.new Teacher 认证\n\n"
            "积分获取:\n"
            "- 注册赠送 1 积分\n"
            "- 每日签到 +1 积分\n"
            "- 邀请好友 +2 积分/人\n"
            "- 使用卡密（按卡密规则）\n"
            f"- 加入频道：{CHANNEL_URL}\n\n"
            "使用方法:\n"
            "1. 在网页开始认证并复制完整的验证链接\n"
            "2. 发送 /verify、/verify2、/verify3、/verify4 或 /verify5 携带该链接\n"
            "3. 等待处理并查看结果\n"
            "4. Bolt.new 认证会自动获取认证码，如需手动查询使用 /getV4Code <verification_id>\n\n"
            "更多命令请发送 /help"
        ),

        # /help
        "help_header": "📖 SheerID 自动认证机器人 - 帮助\n\n用户命令:\n",
        "help_user_commands": (
            "/start - 开始使用（注册）\n"
            "/about - 了解机器人功能\n"
            "/balance - 查看积分余额\n"
            "/lang <en|zh> - 切换语言（英文 / 中文）\n"
            "/qd - 每日签到（+1积分）\n"
            "/invite - 生成邀请链接（+2积分/人）\n"
            "/use <卡密> - 使用卡密兑换积分\n"
            f"/verify <链接> [学校] - Gemini One Pro 认证（-{VERIFY_COST}积分）\n"
            f"/verify2 <链接> - ChatGPT Teacher K12 认证（-{VERIFY_COST}积分）\n"
            f"/verify3 <链接> [学校] - Spotify Student 认证（-{VERIFY_COST}积分）\n"
            f"/verify4 <链接> [学校] - Bolt.new Teacher 认证（-{VERIFY_COST}积分）\n"
            f"/verify5 <链接> [学校] - YouTube Student Premium 认证（-{VERIFY_COST}积分）\n"
            "/getV4Code <verification_id> - 获取 Bolt.new 认证码\n"
            "/help - 查看此帮助信息\n"
            f"认证失败查看：{HELP_NOTION_URL}\n"
        ),
        "help_admin_commands": (
            "\n管理员命令:\n"
            "/addbalance <用户ID> <积分> - 增加用户积分\n"
            "/block <用户ID> - 拉黑用户\n"
            "/white <用户ID> - 取消拉黑\n"
            "/blacklist - 查看黑名单\n"
            "/genkey <卡密> <积分> [次数] [天数] - 生成卡密\n"
            "/listkeys - 查看卡密列表\n"
            "/broadcast <文本> - 向所有用户群发通知\n"
        ),

        # /balance
        "balance_msg": "💰 积分余额\n\n当前积分：{balance} 分",

        # /qd checkin
        "checkin_success": "✅ 签到成功！\n获得积分：+1\n当前积分：{balance} 分",
        "checkin_already": "❌ 今天已经签到过了，明天再来吧。",

        # /invite
        "invite_msg": (
            "🎁 您的专属邀请链接：\n{invite_link}\n\n"
            "每邀请 1 位成功注册，您将获得 2 积分。"
        ),

        # /use card key
        "use_usage": "使用方法: /use <卡密>",
        "key_invalid": "卡密无效或已被完全使用",
        "key_already_used": "您已经使用过此卡密了",
        "key_success": "✅ 卡密使用成功！\n获得积分：+{amount}\n当前积分：{balance} 分",
        "key_failed": "使用卡密失败，请稍后重试",

        # /lang
        "lang_current": "🌐 当前语言：{lang_display}\n\n如需切换语言，请发送：\n/lang en (English)\n/lang zh (中文)",
        "lang_changed": "✅ 已成功切换为中文界面。",
        "lang_invalid": "无效的语言选项。支持：/lang en (English) 或 /lang zh (中文)",

        # Verification messages
        "verify_processing": "⏳ 开始处理验证...\n项目: {service}\nID: {vid}\n请稍候...",
        "verify_success": "🎉 验证成功！\n项目: {service}\n验证 ID: {vid}",
        "verify_failed": "❌ 验证失败: {reason}\n\n已退回 {cost} 积分。",
        "verify_usage": (
            "使用方法: {command} <SheerID链接> [学校]\n\n"
            "示例:\n"
            "{command} https://services.sheerid.com/verify/xxx/?verificationId=xxx ucla\n\n"
            "支持的学校选项：\n"
            "• psu (宾夕法尼亚州立大学 - 默认)\n"
            "• ucla (加州大学洛杉矶分校)\n"
            "• nyu (纽约大学)\n"
            "• umich (密歇根大学)\n"
            "• ut_austin (德克萨斯大学奥斯汀分校)\n\n"
            "获取验证链接:\n"
            "1. 访问 {service_name} 认证页面\n"
            "2. 开始认证流程\n"
            "3. 复制浏览器地址栏中的完整 URL\n"
            "4. 使用 {command} 命令提交"
        ),
    },
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """获取指定语言的国际化翻译文本"""
    target_lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    template = TRANSLATIONS.get(target_lang, {}).get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    try:
        return template.format(**kwargs) if kwargs else template
    except Exception:
        return template


# Alias for backward/forward compatibility
get_text = t


def get_user_lang(user_id: int, db: object | None = None) -> str:
    """Helper to retrieve user's preferred language from DB, defaulting to DEFAULT_LANGUAGE"""
    if db is not None and hasattr(db, "get_user_language"):
        try:
            return db.get_user_language(user_id)
        except Exception:
            pass
    return DEFAULT_LANGUAGE


def get_welcome_message(full_name: str, invited_by: bool = False, lang: str = DEFAULT_LANGUAGE) -> str:
    """获取欢迎消息"""
    invited_note = t("welcome_invited", lang=lang) if invited_by else ""
    return t("welcome", lang=lang, full_name=full_name, invited_note=invited_note)


def get_about_message(lang: str = DEFAULT_LANGUAGE) -> str:
    """获取关于消息"""
    return t("about", lang=lang)


def get_help_message(is_admin: bool = False, lang: str = DEFAULT_LANGUAGE) -> str:
    """获取帮助消息"""
    msg = t("help_header", lang=lang) + t("help_user_commands", lang=lang)
    if is_admin:
        msg += t("help_admin_commands", lang=lang)
    return msg


def get_insufficient_balance_message(current_balance: int, lang: str = DEFAULT_LANGUAGE) -> str:
    """获取积分不足消息"""
    return t("insufficient_balance", lang=lang, balance=current_balance)


def get_verify_usage_message(command: str, service_name: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """获取验证命令使用说明"""
    return t("verify_usage", lang=lang, command=command, service_name=service_name)
