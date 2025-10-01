from unittest.mock import MagicMock


def shared_fix_affected_items(removal_class, queue_data=None):
    # Arrange
    removal_job = removal_class(arr=MagicMock(), settings=MagicMock(), job_name="test")
    if queue_data:
        removal_job.queue = queue_data
    return removal_job


async def shared_test_affected_items(removal_job, expected_download_ids):
    # Act
    affected_items = await removal_job._find_affected_items()  # pylint: disable=W0212

    # Assert
    assert isinstance(affected_items, list)

    # Assert that the affected items match the expected download IDs
    affected_download_ids = [item["downloadId"] for item in affected_items]
    assert sorted(affected_download_ids) == sorted(
        expected_download_ids
    ), f"Expected affected items with downloadIds {expected_download_ids}, got {affected_download_ids}"

    return affected_items
