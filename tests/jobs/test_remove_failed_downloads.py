import pytest

from src.jobs.remove_failed_downloads import RemoveFailedDownloads
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


# Test to check if items with "failed" status are included in affected items with parameterized data
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("queue_data", "expected_download_ids"),
    [
        (
            [
                {"downloadId": "1", "status": "failed"},  # Item with failed status
                {
                    "downloadId": "2",
                    "status": "completed",
                },  # Item with completed status
                {"downloadId": "3"},  # No status field
            ],
            ["1"],  # Only the failed item should be affected
        ),
        (
            [
                {
                    "downloadId": "1",
                    "status": "completed",
                },  # Item with completed status
                {"downloadId": "2", "status": "completed"},
                {"downloadId": "3", "status": "completed"},
            ],
            [],  # No failed items, so no affected items
        ),
        (
            [
                {"downloadId": "1", "status": "failed"},  # Item with failed status
                {"downloadId": "2", "status": "failed"},
            ],
            ["1", "2"],  # Both failed items should be affected
        ),
    ],
)
async def test_find_affected_items(queue_data, expected_download_ids):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveFailedDownloads, queue_data)

    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)
