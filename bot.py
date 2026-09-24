"""Telegram 机器人主程序"""
import logging
from functools import partial

from telegram.error import NetworkError, TimedOut
from telegram.ext import Application, CommandHandler
from telegram.request import HTTPXRequest

from config import BOT_TOKEN
from database_mysql import Database
from handlers.admin_commands import (
    addbalance_command,
    blacklist_command,
    block_command,
    broadcast_command,
    genkey_command,
    listkeys_command,
    white_command,
)
from handlers.user_commands import (
    about_command,
    balance_command,
    checkin_command,
    help_command,
    invite_command,
    lang_command,
    start_command,
    use_command,
)
from handlers.verify_commands import (
    getV4Code_command,
    verify2_command,
    verify3_command,
    verify4_command,
    verify_command,
)

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """全局错误处理"""
    if isinstance(context.error, (TimedOut, NetworkError)):
        logger.warning("网络连接暂时中断/超时: %s", context.error)
        return
    logger.exception("处理更新时发生异常: %s", context.error, exc_info=context.error)


def main():
    """主函数"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in environment variables. Please set BOT_TOKEN in .env file.")
        raise ValueError("BOT_TOKEN is required to run the bot.")

    # 配置 HTTP 客户端超时与重试参数（防止网络波动导致命令回复失败）
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=10.0,
    )

    # 初始化数据库
    db = Database()

    # 创建应用 - 启用并发处理
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .concurrent_updates(True)  # 🔥 关键：启用并发处理多个命令
        .build()
    )

    # 注册用户命令（使用 partial 传递 db 参数）
    application.add_handler(CommandHandler("start", partial(start_command, db=db)))
    application.add_handler(CommandHandler("about", partial(about_command, db=db)))
    application.add_handler(CommandHandler("help", partial(help_command, db=db)))
    application.add_handler(CommandHandler("balance", partial(balance_command, db=db)))
    application.add_handler(CommandHandler("qd", partial(checkin_command, db=db)))
    application.add_handler(CommandHandler("invite", partial(invite_command, db=db)))
    application.add_handler(CommandHandler("use", partial(use_command, db=db)))
    application.add_handler(CommandHandler("lang", partial(lang_command, db=db)))
    application.add_handler(CommandHandler("language", partial(lang_command, db=db)))

    # 注册验证命令
    application.add_handler(CommandHandler("verify", partial(verify_command, db=db)))
    application.add_handler(CommandHandler("verify2", partial(verify2_command, db=db)))
    application.add_handler(CommandHandler("verify3", partial(verify3_command, db=db)))
    application.add_handler(CommandHandler("verify4", partial(verify4_command, db=db)))
    application.add_handler(CommandHandler("getV4Code", partial(getV4Code_command, db=db)))

    # 注册管理员命令
    application.add_handler(CommandHandler("addbalance", partial(addbalance_command, db=db)))
    application.add_handler(CommandHandler("block", partial(block_command, db=db)))
    application.add_handler(CommandHandler("white", partial(white_command, db=db)))
    application.add_handler(CommandHandler("blacklist", partial(blacklist_command, db=db)))
    application.add_handler(CommandHandler("genkey", partial(genkey_command, db=db)))
    application.add_handler(CommandHandler("listkeys", partial(listkeys_command, db=db)))
    application.add_handler(CommandHandler("broadcast", partial(broadcast_command, db=db)))

    # 注册错误处理器
    application.add_error_handler(error_handler)

    logger.info("机器人启动中...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
