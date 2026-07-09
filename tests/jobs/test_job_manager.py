from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from src.job_manager import JobManager


@pytest.mark.asyncio
async def test_run_jobs_keeps_running_when_one_group_raises_request_error():
    settings = MagicMock()
    manager = JobManager(settings)
    arr = MagicMock()
    arr.name = "Sonarr"
    arr.base_url = "http://sonarr:8989"

    with (
        patch.object(
            manager,
            "removal_jobs",
            AsyncMock(side_effect=requests.exceptions.ReadTimeout("timed out")),
        ),
        patch.object(manager, "search_jobs", AsyncMock()) as search_jobs,
    ):
        await manager.run_jobs(arr)

    search_jobs.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_download_client_jobs_handles_per_job_request_errors():
    settings = MagicMock()
    client = MagicMock()
    client.name = "qBittorrent"
    client.base_url = "http://qbittorrent:8080"
    settings.download_clients.qbittorrent = [client]
    settings.download_clients.sabnzbd = []

    manager = JobManager(settings)
    failing_job = MagicMock()
    failing_job.job.enabled = True
    failing_job.job_name = "remove_done_seeding"
    failing_job.run = AsyncMock(
        side_effect=requests.exceptions.ReadTimeout("timed out")
    )

    with (
        patch.object(
            manager, "_download_clients_connected", AsyncMock(return_value=True)
        ),
        patch.object(
            manager,
            "_get_download_client_jobs_for_client",
            MagicMock(return_value=[failing_job]),
        ),
    ):
        result = await manager.run_download_client_jobs()

    assert result == 0
    failing_job.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_download_client_jobs_handles_connection_check_request_errors():
    settings = MagicMock()
    settings.download_clients.qbittorrent = []
    settings.download_clients.sabnzbd = []
    manager = JobManager(settings)

    with patch.object(
        manager,
        "_download_clients_connected",
        AsyncMock(side_effect=requests.exceptions.ReadTimeout("timed out")),
    ):
        result = await manager.run_download_client_jobs()

    assert result is None
