import pytest

from src.jobs.remove_orphans import RemoveOrphans
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("queue_data", "expected_download_ids"),
    [
        (
            [
                {
                    "downloadId": "1",
                    "id": 1,
                    "title": "My Series A - Season 1",
                    "size": 1000,
                    "sizeleft": 500,
                    "downloadClient": "qBittorrent",
                    "protocol": "torrent",
                    "status": "paused",
                    "trackedDownloadState": "downloading",
                    "statusMessages": [],
                },
                {
                    "downloadId": "2",
                    "id": 2,
                    "title": "My Series B - Season 1",
                    "size": 1000,
                    "sizeleft": 500,
                    "downloadClient": "qBittorrent",
                    "protocol": "torrent",
                    "status": "paused",
                    "trackedDownloadState": "downloading",
                    "statusMessages": [],
                },
            ],
            ["1", "2"],
        ),
    ],
)
async def test_find_affected_items(queue_data, expected_download_ids):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveOrphans, queue_data)

    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)
