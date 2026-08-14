"""Token usage logging: per node, per user, only from the two LLM call sites."""

import typing

from app import llm
from app.usage import MemoryUsageLogger, UsageRow, configure_usage_logger, usage_logger


class _FakeRawMessage:
    usage_metadata: typing.ClassVar = {
        "input_tokens": 1200,
        "output_tokens": 340,
        "total_tokens": 1540,
    }


def test_record_usage_from_llm_response(monkeypatch):
    logger = MemoryUsageLogger()
    configure_usage_logger(logger)
    try:
        llm._record("llm_rerank", _FakeRawMessage(), user_id="u-1", run_date="2026-08-14")
        [row] = logger.rows
        assert row == UsageRow(
            user_id="u-1",
            run_date="2026-08-14",
            node="llm_rerank",
            model=row.model,  # whatever ANTHROPIC_MODEL resolves to
            input_tokens=1200,
            output_tokens=340,
        )
    finally:
        configure_usage_logger(MemoryUsageLogger())


def test_missing_usage_metadata_records_zeroes():
    logger = MemoryUsageLogger()
    configure_usage_logger(logger)
    try:
        llm._record("tailor_cv", object(), user_id="u-1", run_date="2026-08-14")
        [row] = logger.rows
        assert (row.input_tokens, row.output_tokens) == (0, 0)
        assert row.node == "tailor_cv"
    finally:
        configure_usage_logger(MemoryUsageLogger())


def test_stub_paths_record_no_usage():
    """Without an API key the stub fallbacks run — and must not log usage."""
    logger = MemoryUsageLogger()
    configure_usage_logger(logger)
    try:
        from app.graph import stubs

        llm.rerank(stubs.SAMPLE_JOBS, stubs.DEFAULT_PROFILE, stubs.SAMPLE_INVENTORY)
        llm.tailor(stubs.SAMPLE_JOBS[0], stubs.SAMPLE_INVENTORY)
        assert logger.rows == []
    finally:
        configure_usage_logger(MemoryUsageLogger())


def test_default_logger_is_memory():
    assert isinstance(usage_logger, MemoryUsageLogger)
