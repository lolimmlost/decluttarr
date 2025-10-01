from unittest.mock import AsyncMock, MagicMock

import pytest

from src.jobs.removal_handler import RemovalHandler


@pytest.mark.parametrize(
    "qbittorrent_configured, is_private, client_type, protocol, expected",
    [
        (True, True, "qbittorrent", "torrent", "private_handling"),
        (True, False, "qbittorrent", "torrent", "public_handling"),
        (False, True, "qbittorrent", "torrent", "remove"),
        (False, False, "qbittorrent", "torrent", "remove"),
        (True, False, "transmission", "torrent", "remove"),  # unsupported client
        (True, False, "myusenetclient", "usenet", "remove"),  # unsupported protocol
    ],
)
@pytest.mark.asyncio
async def test_get_handling_method(
    qbittorrent_configured,
    is_private,
    client_type,
    protocol,
    expected,
):
    # Mock arr
    arr = AsyncMock()
    arr.tracker.private = ["A"] if is_private else []

    # Mock settings and get_download_client_by_name
    settings = MagicMock()
    settings.download_clients.qbittorrent = ["dummy"] if qbittorrent_configured else []

    # Simulate (client_name, client_type) return
    settings.download_clients.get_download_client_by_name.return_value = (
        "client_name",
        client_type,
    )

    settings.general.private_tracker_handling = "private_handling"
    settings.general.public_tracker_handling = "public_handling"

    handler = RemovalHandler(arr=arr, settings=settings, job_name="test")

    affected_download = {
        "downloadClient": "qBittorrent",
        "protocol": protocol,
    }

    result = await handler._get_handling_method(  # pylint: disable=W0212
        "A", affected_download
    )
    assert result == expected
