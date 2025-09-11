"""Tests for the remove_completed job."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.jobs.remove_completed import COMPLETED_STATES, RemoveCompleted


def create_mock_settings(target_tags=None, target_categories=None):
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.jobs = MagicMock()
    settings.jobs.remove_completed.enabled = True
    settings.jobs.remove_completed.target_tags = target_tags or []
    settings.jobs.remove_completed.target_categories = target_categories or []
    settings.general = MagicMock()
    settings.general.protected_tag = "protected"
    return settings


def create_mock_download_client(items: list):
    """Create a mock download client."""
    client = MagicMock()
    client.get_qbit_items = AsyncMock(return_value=items)
    return client


# Default item properties for tests
ITEM_DEFAULTS = {
    "progress": 1,
    "ratio": 0,
    "ratio_limit": -1,
    "seeding_time": 0,
    "seeding_time_limit": -1,
    "tags": "",
    "category": "movies",
    "state": "stoppedUP",
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("item_properties", "target_tags", "target_categories", "should_be_removed"),
    [
        # Ratio limit met, matching tag and category
        (
            {"ratio": 2, "ratio_limit": 2, "tags": "tag1"},
            ["tag1"],
            ["movies"],
            True,
        ),
        # Seeding time limit met, matching tag and category
        (
            {"seeding_time": 100, "seeding_time_limit": 100, "tags": "tag1"},
            ["tag1"],
            ["movies"],
            True,
        ),
        # Neither limit met
        ({"ratio": 1, "ratio_limit": 2}, ["tag1"], ["movies"], False),
        # Progress less than 1 (should not be considered completed)
        (
            {"progress": 0.5, "state": "downloading"},
            ["tag1"],
            ["movies"],
            False,
        ),
        # No matching tags or categories
        (
            {"ratio": 2, "ratio_limit": 2, "tags": "other", "category": "tv"},
            ["tag1"],
            ["movies"],
            False,
        ),
        # Matching category, but not completed
        ({"category": "tv", "state": "downloading"}, [], ["tv"], False),
        # Matching tag, but not completed
        ({"tags": "tag2", "state": "downloading"}, ["tag2"], [], False),
        # Matching category and completed (ratio)
        (
            {"ratio": 2, "ratio_limit": 2, "category": "tv"},
            [],
            ["tv"],
            True,
        ),
        # Matching tag and completed (seeding time)
        (
            {"seeding_time": 100, "seeding_time_limit": 100, "tags": "tag2"},
            ["tag2"],
            [],
            True,
        ),
        # No targets specified
        ({"ratio": 2, "ratio_limit": 2}, [], [], False),
        # Item with multiple tags, one is a target
        (
            {"tags": "tag1,tag2", "ratio": 2, "ratio_limit": 2},
            ["tag2"],
            [],
            True,
        ),
        # Item with a tag that is a substring of a target tag (should not match)
        ({"tags": "tag", "ratio": 2, "ratio_limit": 2}, ["tag1"], [], False),
        # Item with a category that is a substring of a target (should not match)
        (
            {"category": "movie", "ratio": 2, "ratio_limit": 2},
            [],
            ["movies"],
            False,
        ),
        # Test with another completed state
        (
            {"ratio": 2, "ratio_limit": 2, "state": "pausedUP"},
            ["tag1"],
            ["movies"],
            True,
        ),
    ],
)
async def test_remove_completed_logic(
    item_properties: dict,
    target_tags: list,
    target_categories: list,
    should_be_removed: bool,
):
    """Test the logic of the remove_completed job with various scenarios."""
    item = {**ITEM_DEFAULTS, **item_properties, "name": "test_item"}

    settings = create_mock_settings(target_tags, target_categories)
    client = create_mock_download_client([item])

    job = RemoveCompleted(client, "qbittorrent", settings, "remove_completed")

    items_to_remove = await job._get_items_to_remove(await client.get_qbit_items())

    if should_be_removed:
        assert len(items_to_remove) == 1
        assert items_to_remove[0]["name"] == "test_item"
    else:
        assert len(items_to_remove) == 0


@pytest.mark.asyncio
async def test_remove_completed_skipped_for_sabnzbd():
    """Test that the remove_completed job is skipped for SABnzbd clients."""
    settings = create_mock_settings()
    client = create_mock_download_client([])
    job = RemoveCompleted(client, "sabnzbd", settings, "remove_completed")

    # We check the log message instead of mocking the super run
    with patch.object(job.logger, "debug") as mock_log:
        result = await job.run()
        assert result == 0
        mock_log.assert_called_with(
            "Skipping job 'remove_completed' for Usenet client mock_client_name.",
        )


@pytest.mark.asyncio
async def test_remove_completed_test_run_enabled():
    """Test that no items are removed when test_run is enabled."""
    item = {
        **ITEM_DEFAULTS,
        "ratio": 2,
        "ratio_limit": 2,
        "name": "test_item",
        "tags": "tag1",
    }
    settings = create_mock_settings(target_tags=["tag1"])
    settings.general.test_run = True
    client = create_mock_download_client([item])
    job = RemoveCompleted(client, "qbittorrent", settings, "remove_completed")

    with patch.object(
        job,
        "_remove_qbittorrent_item",
        new_callable=AsyncMock,
    ) as mock_remove:
        result = await job.run()

        assert (
            result == 1
        )  # The job should still report the number of items it would have removed
        mock_remove.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("protected_on", ["tag", "category"])
async def test_remove_completed_with_protected_item(protected_on):
    """Test that items with a protected tag or category are not removed."""
    item_properties = {"ratio": 2, "ratio_limit": 2, "name": "protected_item"}
    target_tags = ["tag1"]
    target_categories = ["movies"]

    if protected_on == "tag":
        item_properties["tags"] = "protected"
        # Also add a targetable tag to ensure it's the protection that stops it
        item_properties["tags"] += ",tag1"
    else:
        item_properties["category"] = "protected"

    item = {**ITEM_DEFAULTS, **item_properties}

    settings = create_mock_settings(
        target_tags=target_tags,
        target_categories=target_categories,
    )
    client = create_mock_download_client([item])
    job = RemoveCompleted(client, "qbittorrent", settings, "remove_completed")

    with patch.object(
        job,
        "_remove_qbittorrent_item",
        new_callable=AsyncMock,
    ) as mock_remove:
        result = await job.run()
        assert result == 0  # No items should be removed
        mock_remove.assert_not_called()


@pytest.mark.asyncio
async def test_is_completed_logic():
    """Test the internal _is_completed logic with different states and limits."""
    job = RemoveCompleted(MagicMock(), "qbittorrent", MagicMock(), "remove_completed")

    # Completed states
    for state in COMPLETED_STATES:
        # Ratio met
        assert job._is_completed(
            {"state": state, "ratio": 2, "ratio_limit": 2},
        ), f"Failed for state {state} with ratio met"
        # Seeding time met
        assert job._is_completed(
            {"state": state, "seeding_time": 100, "seeding_time_limit": 100},
        ), f"Failed for state {state} with seeding time met"
        # Neither met
        assert not job._is_completed(
            {"state": state, "ratio": 1, "ratio_limit": 2},
        ), f"Failed for state {state} with neither limit met"
        # Limits not set
        assert not job._is_completed(
            {"state": state, "ratio": 1, "ratio_limit": -1},
        ), f"Failed for state {state} with no ratio limit"

    # Non-completed states
    assert not job._is_completed(
        {"state": "downloading", "ratio": 2, "ratio_limit": 1},
    ), "Failed for non-completed state"
