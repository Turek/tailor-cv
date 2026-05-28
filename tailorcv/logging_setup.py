"""Take over root logging on CLI startup.

Several dependencies (`google.antigravity`, `weasyprint`'s fontTools subsetter,
…) call `logging.basicConfig(...)` at INFO/DEBUG when imported, which floods the
terminal with internal chatter. We reset the root logger to WARNING, drop the
verbose third-party loggers to ERROR, and intercept the SDK's retryable-error
warnings — surfacing them as an inline yellow `retry… ` indicator instead of a
multi-line stack-trace-shaped log line.
"""
from __future__ import annotations

import logging
import re

import click


# Match the Antigravity SDK's retryable-step warning. The SDK uses a single
# canonical template at local_connection.py:585 —
#     logging.warning("System step error (HTTP %s): %s", http_code, error)
# — for every retryable failure: HTTP 5xx ("high demand"), HTTP 0 (transport-
# level), and "Model produced invalid output" responses that the SDK then
# retries. Matching on the prefix catches the whole category at once.
# We keep "retryable" / "high demand" as fallbacks in case the SDK ever
# reformats the line.
_RETRYABLE = re.compile(
    r"System step error|retryable|high demand", re.IGNORECASE
)


class _RetryIndicator(logging.Filter):
    """Convert SDK retry warnings into a compact yellow ``retry… `` chip.

    Returning False from ``filter`` drops the original log record, so the noisy
    multi-line warning never reaches stderr.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING and _RETRYABLE.search(record.getMessage()):
            click.secho("retry… ", fg="yellow", nl=False)
            return False
        return True


# Loggers that are noisy by default and have no business printing INFO/DEBUG
# on a successful CLI run. Set to ERROR so genuine failures still surface.
_NOISY_LOGGERS = (
    "fontTools",
    "weasyprint",
    "google",
    "google.antigravity",
    "google.genai",
    "google_genai",
    "httpx",
    "httpcore",
    "urllib3",
    "asyncio",
    "PIL",
    "anthropic",
)


def configure() -> None:
    """Reset root logging to a quiet, retry-aware setup. Idempotent."""
    root = logging.getLogger()
    # Drop any handlers a dependency installed via basicConfig before us.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    handler.addFilter(_RetryIndicator())
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.setLevel(logging.WARNING)
    root.addHandler(handler)

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
