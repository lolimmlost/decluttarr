from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.settings._instances import ArrInstance


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arr_type, expected_key",
    [
        ("radarr", "movie"),
        ("sonarr", "series"),
    ],
)
async def test_get_refresh_item_calls_make_request_with_correct_params(
    arr_type, expected_key
):
    base_url = f"http://{arr_type}/"
    api_key = "test_key"
    settings = {}

    arr = ArrInstance(settings, arr_type, base_url, api_key)

    # Fake response data your get_refresh_item expects
    fake_json = [{"id": 1, "path": "/media/example"}]

    # Patch make_request to return an object whose .json() coroutine returns fake_json
    with patch(
        "src.settings._instances.make_request", new_callable=AsyncMock
    ) as mock_make_request:
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value=fake_json)
        mock_make_request.return_value = mock_response

        result = await arr.get_refresh_item()

        mock_make_request.assert_awaited_once_with(
            "get",
            arr.api_url + "/" + expected_key,
            settings,
            headers={"X-Api-Key": api_key},
        )
        assert result == fake_json


@pytest.mark.asyncio
async def test_get_refresh_item_by_path_returns_correct_item():
    arr = ArrInstance({}, "radarr", "http://radarr/", "test_key")

    mock_items = [
        {"id": 123, "path": "/media/folder1"},
        {"id": 456, "path": "/media/folder2"},
    ]

    with patch.object(
        arr, "get_refresh_item", AsyncMock(return_value=mock_items)
    ) as mock_method:
        result = await arr.get_refresh_item_by_path("/media/folder2/some_subfolder")

        mock_method.assert_awaited_once()
        assert result == {"id": 456, "path": "/media/folder2"}
