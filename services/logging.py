import sys

from loguru import logger


_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "{extra[channel_ansi]} | "
    "<cyan>{extra[session_short]:<12}</cyan> | "
    "<level>{message}</level>"
)

_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "{extra[channel]:<10} | "
    "{extra[session_short]:<12} | "
    "{message}"
)


def _patch_record(record: dict) -> None:
    extra = record["extra"]
    channel = extra.get("channel", "SYSTEM")
    session = str(extra.get("session_id", "-"))

    channel_styles = {
        "LEAD IN": "\x1b[38;5;214m",
        "AGENT OUT": "\x1b[38;5;77m",
        "SYSTEM": "\x1b[38;5;75m",
    }

    extra["channel"] = channel
    color = channel_styles.get(channel, "\x1b[38;5;245m")
    extra["channel_ansi"] = f"{color}{channel:<10}\x1b[0m"
    extra["session_short"] = session[:12]


def configure_logging() -> None:
    logger.remove()
    logger.configure(patcher=_patch_record)
    logger.add(
        sys.stdout,
        level="INFO",
        format=_CONSOLE_FORMAT,
        colorize=True,
        enqueue=False,
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        level="INFO",
        format=_FILE_FORMAT,
        colorize=False,
        enqueue=False,
        backtrace=False,
        diagnose=False,
    )


def log_lead_message(session_id: str, message: str) -> None:
    logger.bind(channel="LEAD IN", session_id=session_id).info(message)


def log_agent_message(session_id: str, message: str) -> None:
    logger.bind(channel="AGENT OUT", session_id=session_id).info(message)
