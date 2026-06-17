from unittest.mock import MagicMock

import pytest

from src.jobs.remove_metadata_missing import RemoveMetadataMissing
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


# Test to check if items with the specific error message are included in affected items with parameterized data
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("queue_data", "expected_download_ids"),
    [
        (
            [
                {
                    "downloadId": "1",
                    "status": "queued",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Valid item
                {
                    "downloadId": "2",
                    "status": "completed",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Wrong status
                {
                    "downloadId": "3",
                    "status": "queued",
                    "errorMessage": "Some other error",
                },  # Incorrect errorMessage
            ],
            [
                "1"
            ],  # Only the item with "queued" status and the correct errorMessage should be affected
        ),
        (
            [
                {
                    "downloadId": "1",
                    "status": "queued",
                    "errorMessage": "Some other error",
                },  # Incorrect errorMessage
                {
                    "downloadId": "2",
                    "status": "completed",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Wrong status
                {
                    "downloadId": "3",
                    "status": "queued",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Correct item
            ],
            [
                "3"
            ],  # Only the item with "queued" status and the correct errorMessage should be affected
        ),
        (
            [
                {
                    "downloadId": "1",
                    "status": "queued",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Valid item
                {
                    "downloadId": "2",
                    "status": "queued",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Another valid item
            ],
            ["1", "2"],  # Both items match the condition
        ),
        (
            [
                {
                    "downloadId": "1",
                    "status": "completed",
                    "errorMessage": "qBittorrent is downloading metadata",
                },  # Wrong status
                {
                    "downloadId": "2",
                    "status": "queued",
                    "errorMessage": "Some other error",
                },  # Incorrect errorMessage
            ],
            [],  # No items match the condition
        ),
    ],
)
async def test_find_affected_items(queue_data, expected_download_ids):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveMetadataMissing, queue_data)

    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)


# Tests the opt-in, client-agnostic detection of items stuck without metadata
# (status "queued" + size 0), e.g. on Transmission/Deluge which do not surface the
# qBittorrent "downloading metadata" message in the *arr queue (see issue #57).
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("detect_via_missing_size", "queue_data", "expected_download_ids"),
    [
        # Disabled (default): a queued size-0 item is NOT flagged; only the qBit message is.
        (
            False,
            [
                {
                    "id": 1,
                    "downloadId": "a",
                    "status": "queued",
                    "size": 0,
                    "errorMessage": None,
                },
                {
                    "id": 2,
                    "downloadId": "b",
                    "status": "queued",
                    "errorMessage": "qBittorrent is downloading metadata",
                },
            ],
            ["b"],
        ),
        # Enabled: queued + size 0 is flagged; size > 0 and non-queued are left alone.
        (
            True,
            [
                {
                    "id": 1,
                    "downloadId": "a",
                    "status": "queued",
                    "size": 0,
                    "errorMessage": None,
                },
                {
                    "id": 2,
                    "downloadId": "b",
                    "status": "queued",
                    "size": 1234,
                    "errorMessage": None,
                },
                {
                    "id": 3,
                    "downloadId": "c",
                    "status": "downloading",
                    "size": 0,
                    "errorMessage": None,
                },
            ],
            ["a"],
        ),
        # Enabled: an item matching BOTH the qBit message and size 0 is not duplicated.
        (
            True,
            [
                {
                    "id": 1,
                    "downloadId": "a",
                    "status": "queued",
                    "size": 0,
                    "errorMessage": "qBittorrent is downloading metadata",
                },
                {
                    "id": 2,
                    "downloadId": "b",
                    "status": "queued",
                    "size": 0,
                    "errorMessage": None,
                },
            ],
            ["a", "b"],
        ),
        # Enabled but no size key present (e.g. partial item): not matched.
        (
            True,
            [
                {"id": 1, "downloadId": "a", "status": "queued", "errorMessage": None},
            ],
            [],
        ),
    ],
)
async def test_find_affected_items_via_missing_size(
    detect_via_missing_size, queue_data, expected_download_ids
):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveMetadataMissing, queue_data)
    removal_job.job = MagicMock(detect_via_missing_size=detect_via_missing_size)

    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)
