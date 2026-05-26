"""A Typesense backend failure during commit must not abort the transaction
that is saving the user's content.

Regression test: creating/editing content while Typesense is unreachable used
to raise ``httpx.ConnectError`` out of the indexing queue's ``commit_ts`` while
the transaction was in ``tpc_finish``, which broke content operations entirely.
The content lives in the ZODB regardless of the search backend, so indexing
failures must be logged and swallowed, not propagated.
"""
from unittest.mock import MagicMock

import httpx
import pytest
from typesense import exceptions as typesense_exceptions

from plone.typesense.interfaces import IndexingActions
from plone.typesense.queueprocessor import IndexProcessor


def _make_processor(side_effect=None):
    """Build an IndexProcessor wired with a mocked, "enabled" connector."""
    proc = IndexProcessor()
    connector = MagicMock()
    connector.enabled = True
    if side_effect is not None:
        connector.index.side_effect = side_effect
    proc._ts_connector = connector
    # A truthy client so commit_ts proceeds to flush the queue.
    proc._ts_client = MagicMock()
    proc._actions = IndexingActions(
        index={"uuid1": {"id": "uuid1", "title": "Test Page"}},
        reindex={},
        unindex={},
        index_blobs={},
        uuid_path={"uuid1": "/Plone/test-page"},
    )
    return proc, connector


class TestCommitResilience:
    """commit_ts must survive an unreachable / failing Typesense backend."""

    def test_connection_refused_does_not_propagate(self):
        """A refused connection (httpx.ConnectError) is swallowed."""
        proc, connector = _make_processor(
            side_effect=httpx.ConnectError("[Errno 111] Connection refused")
        )
        # Must not raise.
        proc.commit_ts()
        connector.index.assert_called_once()

    def test_typesense_client_error_does_not_propagate(self):
        """A Typesense client error (e.g. server error) is swallowed."""
        proc, connector = _make_processor(
            side_effect=typesense_exceptions.TypesenseClientError("boom")
        )
        proc.commit_ts()
        connector.index.assert_called_once()

    def test_timeout_does_not_propagate(self):
        """A request timeout is swallowed."""
        proc, connector = _make_processor(side_effect=httpx.ReadTimeout("timed out"))
        proc.commit_ts()
        connector.index.assert_called_once()

    def test_actions_cleaned_up_after_failure(self):
        """The queue is cleared even when the backend call fails, so a
        retried/aborted commit does not re-flush stale actions."""
        proc, _ = _make_processor(
            side_effect=httpx.ConnectError("[Errno 111] Connection refused")
        )
        proc.commit_ts()
        assert proc._actions is None

    def test_successful_commit_still_indexes(self):
        """When the backend is healthy the index call is made normally."""
        proc, connector = _make_processor()
        proc.commit_ts()
        connector.index.assert_called_once()
        # The payload's id is rewritten to the uuid before sending.
        sent = connector.index.call_args[0][0]
        assert sent[0]["id"] == "uuid1"

    def test_unexpected_error_still_propagates(self):
        """Non-backend errors (genuine bugs) are not masked by the guard."""
        proc, _ = _make_processor(side_effect=ValueError("programming error"))
        with pytest.raises(ValueError):
            proc.commit_ts()
