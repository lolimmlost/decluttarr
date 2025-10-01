import pytest

from src.jobs.remove_missing_files import RemoveMissingFiles
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("queue_data", "expected_download_ids"),
    [
        (
            [  # valid failed torrent (warning + matching errorMessage)
                {
                    "downloadId": "1",
                    "status": "warning",
                    "errorMessage": "DownloadClientQbittorrentTorrentStateMissingFiles",
                },
                {
                    "downloadId": "2",
                    "status": "warning",
                    "errorMessage": "The download is missing files",
                },
                {
                    "downloadId": "3",
                    "status": "warning",
                    "errorMessage": "qBittorrent is reporting missing files",
                },
            ],
            ["1", "2", "3"],
        ),
        (
            [  # wrong status for errorMessage, should be ignored
                {
                    "downloadId": "1",
                    "status": "failed",
                    "errorMessage": "The download is missing files",
                },
            ],
            [],
        ),
        (
            [  # valid "completed" with matching statusMessage
                {
                    "downloadId": "1",
                    "status": "completed",
                    "statusMessages": [
                        {
                            "messages": [
                                "No files found are eligible for import in /some/path"
                            ]
                        },
                    ],
                },
                {
                    "downloadId": "2",
                    "status": "completed",
                    "statusMessages": [
                        {"messages": ["Everything looks good!"]},
                    ],
                },
            ],
            ["1"],
        ),
        (
            [  # No statusMessages key or irrelevant messages
                {"downloadId": "1", "status": "completed"},
                {
                    "downloadId": "2",
                    "status": "completed",
                    "statusMessages": [{"messages": ["Other message"]}],
                },
            ],
            [],
        ),
        (
            [  # Mixed: one matching warning + one matching statusMessage
                {
                    "downloadId": "1",
                    "status": "warning",
                    "errorMessage": "The download is missing files",
                },
                {
                    "downloadId": "2",
                    "status": "completed",
                    "statusMessages": [
                        {"messages": ["No files found are eligible for import in foo"]}
                    ],
                },
                {"downloadId": "3", "status": "completed"},
            ],
            ["1", "2"],
        ),
    ],
)
async def test_find_affected_items(queue_data, expected_download_ids):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveMissingFiles, queue_data)

    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)
