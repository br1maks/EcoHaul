
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    log_format = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    app_log_file = log_path / "app.log"
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(log_format)
    root_logger.addHandler(app_handler)

    error_log_file = log_path / "error.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)

    payment_log_file = log_path / "payments.log"
    payment_handler = RotatingFileHandler(
        payment_log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    payment_handler.setLevel(logging.INFO)
    payment_handler.setFormatter(log_format)

    payment_logger = logging.getLogger("app.api.v1.payments")
    payment_logger.addHandler(payment_handler)

    subscription_logger = logging.getLogger("app.api.v1.subscriptions")
    subscription_logger.addHandler(payment_handler)

    yookassa_logger = logging.getLogger("app.services.yookassa_service")
    yookassa_logger.addHandler(payment_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root_logger.info(f"Logging configured: level={log_level}, dir={log_dir}")

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
