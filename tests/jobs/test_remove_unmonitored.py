from unittest.mock import AsyncMock

import pytest

from src.jobs.remove_unmonitored import RemoveUnmonitored
from tests.jobs.utils import shared_fix_affected_items, shared_test_affected_items


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("queue_data", "monitored_ids", "expected_download_ids"),
    [
        # All items monitored -> no affected items
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "2", "detail_item_id": 102},
            ],
            {101: True, 102: True},
            [],
        ),
        # All items unmonitored -> all affected
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "2", "detail_item_id": 102},
            ],
            {101: False, 102: False},
            ["1", "2"],
        ),
        # One monitored, one not
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "2", "detail_item_id": 102},
            ],
            {101: True, 102: False},
            ["2"],
        ),
        # Shared downloadId, only one monitored -> not affected
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "1", "detail_item_id": 102},
            ],
            {101: False, 102: True},
            [],
        ),
        # Shared downloadId, none monitored -> affected
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "1", "detail_item_id": 102},
            ],
            {101: False, 102: False},
            ["1", "1"],
        ),
        # One monitored, one not, one not matched yet
        (
            [
                {"downloadId": "1", "detail_item_id": 101},
                {"downloadId": "2", "detail_item_id": 102},
                {"downloadId": "3", "detail_item_id": None},
            ],
            {101: True, 102: False},
            ["2"],
        ),
    ],
)
async def test_find_affected_items(queue_data, monitored_ids, expected_download_ids):
    # Arrange
    removal_job = shared_fix_affected_items(RemoveUnmonitored, queue_data)
    removal_job.arr.is_monitored = AsyncMock(side_effect=lambda id_: monitored_ids[id_])
    # Act and Assert
    await shared_test_affected_items(removal_job, expected_download_ids)
