"""Configure application logging for console and rotating file output.

Importing this module creates the project-local log directory, applies the
process-wide logging configuration, and exposes the named application logger.
"""

import logging
from logging.config import dictConfig
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "logs" / "h2_system"
LOG_FILE = LOG_DIR / "activity.log"

# Resolve logs from the project root so startup location cannot redirect output.
LOG_DIR.mkdir(parents=True, exist_ok=True)

dictConfig(
    {
        "version": 1,
        # Preserve framework loggers such as Werkzeug request logging.
        "disable_existing_loggers": False,
        "formatters": {
            "console_standard": {
                "format": "[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "file_detailed": {
                "format": (
                    "[%(asctime)s] %(levelname)-7s "
                    "[%(filename)s:%(lineno)d] - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console_standard",
                "stream": "ext://sys.stdout",
            },
            "application_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file_detailed",
                "filename": str(LOG_FILE),
                "maxBytes": 2 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        # The root receives application and third-party records at INFO or above.
        "root": {
            "handlers": ["console", "application_file"],
            "level": "INFO",
        },
    }
)

logger = logging.getLogger("H2_Generator_API")


__all__ = ["logger"]