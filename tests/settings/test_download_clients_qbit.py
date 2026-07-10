import pytest
from requests.cookies import RequestsCookieJar

from src.settings._download_clients_qbit import QbitClient, QbitError


@pytest.mark.parametrize(
    "cookie_name, cookie_value, expected",
    [
        # Legacy format
        ("SID", "abc", {"SID": "abc"}),
        # New dynamic port format (qBit 5.2+)
        ("QBT_SID_8080", "xyz", {"QBT_SID_8080": "xyz"}),
        ("QBT_SID_12345", "token123", {"QBT_SID_12345": "token123"}),
    ],
)
def test_extract_sid_success(cookie_name, cookie_value, expected):
    """Test successful extraction for various valid cookie names."""
    jar = RequestsCookieJar()
    jar.set(cookie_name, cookie_value)

    assert QbitClient.extract_sid(jar) == expected


@pytest.mark.parametrize(
    "cookies",
    [
        {},  # Empty jar
        {"WRONG_NAME": "value"},  # Incorrect name
        {"sid": "lowercase_fails"},  # Case sensitivity check
    ],
)
def test_extract_sid_failures(cookies):
    """Test that invalid cookies properly raise QbitError."""
    jar = RequestsCookieJar()
    for name, val in cookies.items():
        jar.set(name, val)

    with pytest.raises(QbitError, match="No qBit cookie found"):
        QbitClient.extract_sid(jar)


from unittest.mock import AsyncMock, MagicMock, patch

import requests


@pytest.mark.asyncio
async def test_setup_reachability_timeout_marks_transient():
    settings = MagicMock()
    client = QbitClient(settings, base_url="http://qbit:8080")

    with patch(
        "src.settings._download_clients_qbit.make_request",
        new_callable=AsyncMock,
        side_effect=requests.exceptions.ReadTimeout("Read timed out."),
    ):
        result = await client.setup()

    assert result is False
    assert client.ready is False
    assert client.failure_kind == "transient"
    assert "Read timed out." in client.last_error


@pytest.mark.asyncio
async def test_setup_old_version_marks_definitive():
    settings = MagicMock()
    settings.min_versions.qbittorrent = "4.3.0"
    client = QbitClient(settings, base_url="http://qbit:8080")
    client.check_qbit_reachability = AsyncMock()
    client.refresh_cookie = AsyncMock()
    client.fetch_version = AsyncMock()
    client.version = "3.0.0"

    await client.setup()

    assert client.ready is False
    assert client.failure_kind == "definitive"


@pytest.mark.asyncio
async def test_setup_cookie_refresh_failure_marks_transient():
    settings = MagicMock()
    client = QbitClient(settings, base_url="http://qbit:8080")
    client.check_qbit_reachability = AsyncMock()
    client.refresh_cookie = AsyncMock(
        side_effect=QbitError(ConnectionError("Login failed."))
    )

    await client.setup()

    assert client.ready is False
    assert client.failure_kind == "transient"


@pytest.mark.asyncio
async def test_setup_bad_password_marks_definitive():
    """Wrong qBit password (HTTP 200 + 'Fails.') is definitive, not retried forever."""
    settings = MagicMock()
    client = QbitClient(
        settings, base_url="http://qbit:8080", username="u", password="wrong"
    )
    resp = MagicMock(text="Fails.")
    with patch(
        "src.settings._download_clients_qbit.make_request",
        new_callable=AsyncMock,
        return_value=resp,
    ):
        await client.setup()

    assert client.ready is False
    assert client.failure_kind == "definitive"
