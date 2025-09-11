from abc import ABC, abstractmethod

from src.utils.common import make_request
from src.utils.log_setup import logger


class DownloadClientRemovalJob(ABC):
    """Base class for removal jobs that run on download clients directly."""

    job_name = None

    def __init__(
        self,
        download_client: object,
        download_client_type: str,
        settings: object,
        job_name: str,
    ) -> None:
        self.download_client = download_client
        self.download_client_type = download_client_type
        self.settings = settings
        self.job_name = job_name
        self.job = getattr(self.settings.jobs, self.job_name)

    async def run(self) -> int:
        """Run the download client job."""
        if not self.job.enabled:
            return 0

        logger.debug(
            f"download_client_job.py/run: Launching job '{self.job_name}' on {self.download_client.name} "
            f"({self.download_client_type})",
        )

        all_items = await self._get_all_items()
        if not all_items:
            return 0

        items_to_remove = await self._get_items_to_remove(all_items)

        # Filter out protected items
        items_to_remove = self._filter_protected_items(items_to_remove)

        if not items_to_remove:
            logger.debug(f"No items to remove for job '{self.job_name}'.")
            return 0

        # Remove the affected items
        await self._remove_items(items_to_remove)

        return len(items_to_remove)

    async def _get_all_items(self) -> list:
        """Get all items from the download client."""
        try:
            if self.download_client_type == "qbittorrent":
                return await self.download_client.get_qbit_items()
            if self.download_client_type == "sabnzbd":
                return await self.download_client.get_history_items()
        except Exception as e:
            logger.error(
                f"Error fetching items from {self.download_client.name}: {e}",
            )
        return []

    def _filter_protected_items(self, items: list) -> list:
        """Filter out items that are protected by tags or categories."""
        protected_tag = getattr(self.settings.general, "protected_tag", None)
        if not protected_tag:
            return items

        filtered_items = []
        for item in items:
            is_protected = False
            item_name = item.get("name", "unknown")
            if self.download_client_type == "qbittorrent":
                tags = item.get("tags", "").split(",")
                tags = [tag.strip() for tag in tags if tag.strip()]
                category = item.get("category", "")
                if protected_tag in tags or protected_tag == category:
                    is_protected = True
            elif self.download_client_type == "sabnzbd":
                category = item.get("category", "")
                if protected_tag == category:
                    is_protected = True

            if is_protected:
                logger.debug(f"Ignoring protected item: {item_name}")
            else:
                filtered_items.append(item)

        return filtered_items

    @abstractmethod
    async def _get_items_to_remove(self, items: list) -> list:
        """Return a list of items to remove from the download client."""

    async def _remove_items(self, items: list) -> None:
        """Remove the affected items from the download client."""
        if self.settings.general.test_run:
            logger.info("Test run is enabled. Skipping actual removal.")
            for item in items:
                item_name = item.get("name", "unknown")
                logger.info(f"Would have removed download: {item_name}")
            return

        for item in items:
            item_name = item.get("name", "unknown")
            try:
                if self.download_client_type == "qbittorrent":
                    await self._remove_qbittorrent_item(item)
                elif self.download_client_type == "sabnzbd":
                    await self._remove_sabnzbd_item(item)

                logger.info(
                    f"Removed download: {item_name}",
                )

            except Exception as e:
                logger.error(f"Failed to remove {item_name}: {e}")

    async def _remove_qbittorrent_item(self, item: dict) -> None:
        """Remove a torrent from qBittorrent."""
        download_id = item["hash"].lower()
        data = {
            "hashes": download_id,
            "deleteFiles": "true",
        }
        await make_request(
            "post",
            f"{self.download_client.api_url}/torrents/delete",
            self.settings,
            data=data,
            cookies=self.download_client.cookie,
        )

    async def _remove_sabnzbd_item(self, item: dict) -> None:
        """Remove a download from SABnzbd history."""
        download_id = item["nzo_id"]
        params = {
            "mode": "history",
            "name": "delete",
            "value": download_id,
            "apikey": self.download_client.api_key,
            "output": "json",
        }
        await make_request(
            "get",
            self.download_client.api_url,
            self.settings,
            params=params,
        )
