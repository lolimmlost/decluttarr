from unittest.mock import MagicMock

import pytest

from src.jobs.remove_failed_imports import RemoveFailedImports
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("item", "expected_result"),
    [
        # Valid item scenario
        (
            {
                "status": "completed",
                "trackedDownloadStatus": "warning",
                "trackedDownloadState": "importPending",
                "statusMessages": [{"messages": ["Import failed"]}],
            },
            True,
        ),
        # Invalid item with wrong status
        (
            {
                "status": "downloading",
                "trackedDownloadStatus": "warning",
                "trackedDownloadState": "importPending",
                "statusMessages": [{"messages": ["Import failed"]}],
            },
            False,
        ),
        # Invalid item with missing required fields
        (
            {
                "trackedDownloadStatus": "warning",
                "trackedDownloadState": "importPending",
                "statusMessages": [{"messages": ["Import failed"]}],
            },
            False,
        ),
        # Invalid item with wrong trackedDownloadStatus
        (
            {
                "status": "completed",
                "trackedDownloadStatus": "downloading",
                "trackedDownloadState": "importPending",
                "statusMessages": [{"messages": ["Import failed"]}],
            },
            False,
        ),
        # Invalid item with wrong trackedDownloadState
        (
            {
                "status": "completed",
                "trackedDownloadStatus": "warning",
                "trackedDownloadState": "downloaded",
                "statusMessages": [{"messages": ["Import failed"]}],
            },
            False,
        ),
    ],
)
async def test_is_valid_item(item, expected_result):
    # Fix
    removal_job = RemoveFailedImports(
        arr=MagicMock(), settings=MagicMock(), job_name="test"
    )

    # Act
    result = removal_job._is_valid_item(item)  # pylint: disable=W0212

    # Assert
    assert result == expected_result


# Fixture with 3 valid items with different messages and downloadId
@pytest.fixture(name="queue_data")
def fixture_queue_data():
    return [
        {
            "downloadId": "1",
            "status": "completed",
            "trackedDownloadStatus": "warning",
            "trackedDownloadState": "importPending",
            "statusMessages": [{"messages": ["Import failed due to issue A"]}],
        },
        {
            "downloadId": "2",
            "status": "completed",
            "trackedDownloadStatus": "warning",
            "trackedDownloadState": "importFailed",
            "statusMessages": [{"messages": ["Import failed due to issue B"]}],
        },
        {
            "downloadId": "3",
            "status": "completed",
            "trackedDownloadStatus": "warning",
            "trackedDownloadState": "importBlocked",
            "statusMessages": [{"messages": ["Import blocked due to issue C"]}],
        },
    ]


# Test the different patterns and check if the right downloads are selected
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("patterns", "expected_download_ids", "removal_messages_expected"),
    [
        (["*"], ["1", "2", "3"], True),  # Match everything, expect removal messages
        (
            ["Import failed*"],
            ["1", "2"],
            True,
        ),  # Match "Import failed", expect removal messages
        (
            ["Import blocked*"],
            ["3"],
            True,
        ),  # Match "Import blocked", expect removal messages
        (
            ["*due to issue A"],
            ["1"],
            True,
        ),  # Match "due to issue A", expect removal messages
        (
            ["Import failed due to issue C"],
            [],
            False,
        ),  # No match for "Import failed due to issue C", expect no removal messages
    ],
)
async def test_find_affected_items_with_patterns(
    queue_data, patterns, expected_download_ids, removal_messages_expected
):

    # Arrange
    removal_job = shared_fix_affected_items(RemoveFailedImports, queue_data)

    # Mock the job settings for message patterns
    removal_job.job = MagicMock()
    removal_job.job.message_patterns = patterns

    # Act and Assert (Shared)
    affected_items = await shared_test_affected_items(
        removal_job, expected_download_ids
    )

    # Check if the correct downloadIds are in the affected items
    affected_download_ids = [item["downloadId"] for item in affected_items]

    # Assert the affected download IDs are as expected
    assert sorted(affected_download_ids) == sorted(expected_download_ids)

    # Check if removal messages are expected and present
    for item in affected_items:
        if removal_messages_expected:
            assert (
                "removal_messages" in item
            ), f"Expected removal messages for item {item['downloadId']}"
            assert (
                len(item["removal_messages"]) > 0
            ), f"Expected non-empty removal messages for item {item['downloadId']}"
        else:
            assert (
                "removal_messages" not in item
            ), f"Did not expect removal messages for item {item['downloadId']}"
