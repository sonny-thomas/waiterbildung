import logging

COLORS = {
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",  # Reset
}


class ColorFormatter(logging.Formatter):
    def __init__(self, fmt: str) -> None:
        super().__init__(fmt)
        self.max_length = max(len(name) for name in COLORS.keys() if name != "RESET")

    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, COLORS["RESET"])
        level_name = record.levelname
        padding = " " * (self.max_length - len(level_name))
        record.levelname = f"{color}{level_name}{COLORS['RESET']}"
        self._style._fmt = f"%(levelname)s:{padding} %(message)s"
        return super().format(record)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    return logger


logger = setup_logger()
