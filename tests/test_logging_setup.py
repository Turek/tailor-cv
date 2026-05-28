"""Tests for the root-logger takeover."""
from __future__ import annotations

import logging

import click
from click.testing import CliRunner

from tailorcv import logging_setup


def _reset_root():
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.WARNING)


def test_configure_drops_preexisting_handlers():
    _reset_root()
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())
    assert len(root.handlers) == 1

    logging_setup.configure()

    # One handler from configure(), the prior basicConfig-style one is gone.
    assert len(root.handlers) == 1


def test_configure_silences_noisy_loggers():
    _reset_root()
    logging_setup.configure()
    for name in ("fontTools", "weasyprint", "google.antigravity", "httpx"):
        assert logging.getLogger(name).level == logging.ERROR


def test_configure_drops_info_and_debug_records(capsys):
    _reset_root()
    logging_setup.configure()
    log = logging.getLogger("some.random.lib")
    log.info("noisy info")
    log.debug("noisy debug")
    captured = capsys.readouterr()
    assert "noisy info" not in captured.err
    assert "noisy info" not in captured.out
    assert "noisy debug" not in captured.err


def test_retryable_warning_becomes_yellow_retry_chip():
    """SDK retry warnings collapse into an inline yellow ``retry… `` indicator."""
    _reset_root()
    logging_setup.configure()
    log = logging.getLogger("root")

    runner = CliRunner()

    @click.command()
    def emit():
        log.warning(
            "System step error (HTTP 503): Encountered retryable error: high demand"
        )

    result = runner.invoke(emit, color=True)
    # The filter prints the chip via click.secho before dropping the record.
    assert "retry…" in result.output
    # The original noisy message is suppressed.
    assert "System step error" not in result.output
    # Yellow ANSI sequence is present (color=True propagates secho's styling).
    assert "\x1b[33m" in result.output


def test_retry_chip_catches_http_0_invalid_output():
    """HTTP 0 / 'Model produced invalid output' is also a retryable category."""
    _reset_root()
    logging_setup.configure()
    log = logging.getLogger("root")

    runner = CliRunner()

    @click.command()
    def emit():
        log.warning(
            'System step error (HTTP 0): Model produced invalid output. '
            '("model output error: ...")'
        )

    result = runner.invoke(emit, color=True)
    assert "retry…" in result.output
    assert "System step error" not in result.output
    assert "Model produced invalid output" not in result.output


def test_non_retryable_warning_passes_through(capsys):
    """A genuine warning unrelated to retries still surfaces."""
    _reset_root()
    logging_setup.configure()
    logging.getLogger("app").warning("disk is almost full")
    captured = capsys.readouterr()
    assert "disk is almost full" in captured.err
