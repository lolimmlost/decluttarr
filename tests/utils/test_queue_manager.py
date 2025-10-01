from unittest.mock import Mock

import pytest

from src.utils.queue_manager import QueueManager


# ---------- Fixtures ----------
@pytest.fixture(name="mock_queue_manager")
def fixture_mock_queue_manager():
    mock_arr = Mock()
    mock_settings = Mock()
    return QueueManager(arr=mock_arr, settings=mock_settings)


# ---------- Tests ----------
def test_format_queue_empty(mock_queue_manager):
    result = mock_queue_manager.format_queue([])
    assert result == "empty"


def test_format_queue_single_item(mock_queue_manager):
    queue_items = [
        {
            "downloadId": "abc123",
            "title": "Example Download Title",
            "protocol": "torrent",
            "status": "queued",
            "id": 1,
        }
    ]
    expected = {
        "abc123": {
            "title": "Example Download Title",
            "protocol": "torrent",
            "status": "queued",
            "queue_ids": [1],
        }
    }
    result = mock_queue_manager.format_queue(queue_items)
    assert result == expected


def test_format_queue_multiple_same_download_id(mock_queue_manager):
    queue_items = [
        {
            "downloadId": "xyz789",
            "title": "Example Download Title",
            "protocol": "usenet",
            "status": "downloading",
            "id": 1,
        },
        {
            "downloadId": "xyz789",
            "title": "Example Download Title",
            "protocol": "usenet",
            "status": "downloading",
            "id": 2,
        },
    ]
    expected = {
        "xyz789": {
            "title": "Example Download Title",
            "protocol": "usenet",
            "status": "downloading",
            "queue_ids": [1, 2],
        }
    }
    result = mock_queue_manager.format_queue(queue_items)
    assert result == expected


def test_format_queue_multiple_different_download_ids(mock_queue_manager):
    queue_items = [
        {
            "downloadId": "aaa111",
            "title": "Example Download Title A",
            "protocol": "torrent",
            "status": "queued",
            "id": 10,
        },
        {
            "downloadId": "bbb222",
            "title": "Example Download Title B",
            "protocol": "usenet",
            "status": "completed",
            "id": 20,
        },
    ]
    expected = {
        "aaa111": {
            "queue_ids": [10],
            "title": "Example Download Title A",
            "protocol": "torrent",
            "status": "queued",
        },
        "bbb222": {
            "queue_ids": [20],
            "title": "Example Download Title B",
            "protocol": "usenet",
            "status": "completed",
        },
    }
    result = mock_queue_manager.format_queue(queue_items)
    assert result == expected
