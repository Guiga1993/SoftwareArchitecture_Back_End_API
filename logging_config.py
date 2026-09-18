"""Configure application logging for console and rotating file output.

Importing this module creates the project-local log directory, applies the
process-wide logging configuration, and exposes the named application logger.
"""

import logging
import os
from logging.config import dictConfig
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "logs" / "h2_system"
LOG_FILE = LOG_DIR / "activity.log"

# Resolve logs from the project root so startup location cannot redirect output.
LOG_DIR.mkdir(parents=True, exist_ok=True)


def parse_file_logging_enabled() -> bool:
    """Return whether rotating file logs are enabled for this process."""
    raw_value = os.getenv("BACKEND_FILE_LOGGING_ENABLED", "true").strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(
        "BACKEND_FILE_LOGGING_ENABLED must be one of: "
        "0, 1, false, no, off, on, true, yes"
    )


root_handlers = ["console"]
if parse_file_logging_enabled():
    root_handlers.append("application_file")

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
            "handlers": root_handlers,
            "level": "INFO",
        },
    }
)

logger = logging.getLogger("H2_Generator_API")


__all__ = ["logger", "parse_file_logging_enabled"]