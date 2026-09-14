"""Structured logging utility for JARVIS."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", record.name),
            "message": record.getMessage(),
        }

        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    default_component: str = "jarvis.core"
) -> logging.Logger:
    """Configures the root logger with structured output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        standard_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        handler.setFormatter(logging.Formatter(standard_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger.addHandler(handler)
    return logging.getLogger(default_component)


def get_logger(component: str, correlation_id: Optional[str] = None) -> logging.LoggerAdapter:
    """Returns a LoggerAdapter with injected component name and optional correlation ID."""
    base_logger = logging.getLogger(component)
    extra = {"component": component, "correlation_id": correlation_id}
    return logging.LoggerAdapter(base_logger, extra)
