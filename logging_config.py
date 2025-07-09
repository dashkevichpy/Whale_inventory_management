import logging
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Configure application logging."""
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        "app.log", maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console])