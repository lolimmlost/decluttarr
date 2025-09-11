"""Removes completed torrents that have specific tags/categories."""

from src.jobs.download_client_removal_job import DownloadClientRemovalJob
from src.utils.log_setup import logger

COMPLETED_STATES = [
    "stoppedUP",
    "pausedUP",  # Older qBittorrent versions
]


class RemoveCompleted(DownloadClientRemovalJob):
    """Job to remove completed torrents that match specific tags or categories."""

    async def run(self) -> int:
        if self.download_client_type == "sabnzbd":
            logger.debug(
                f"Skipping job '{self.job_name}' for Usenet client {self.download_client.name}.",
            )
            return 0
        return await super().run()

    async def _get_items_to_remove(self, items: list) -> list:
        """
        Filters a list of items from a download client and returns those
        that should be removed based on completion status and other criteria.
        """
        target_tags, target_categories = self._get_targets()

        if not target_tags and not target_categories:
            logger.debug(
                "No target tags or categories specified for remove_completed job.",
            )
            return []

        items_to_remove = [
            item
            for item in items
            if self._is_completed(item)
            and self._meets_target_criteria(item, target_tags, target_categories)
        ]

        for item in items_to_remove:
            logger.debug(
                f"Found completed item to remove: {item.get('name', 'unknown')}",
            )

        return items_to_remove

    def _is_completed(self, item: dict) -> bool:
        """Check if an item has met its seeding goals."""
        state = item.get("state", "")
        if state not in COMPLETED_STATES:
            return False

        # Additional sanity checks for ratio and seeding time
        ratio = item.get("ratio", 0)
        ratio_limit = item.get("ratio_limit", -1)
        seeding_time = item.get("seeding_time", 0)
        seeding_time_limit = item.get("seeding_time_limit", -1)

        ratio_limit_met = ratio >= ratio_limit > 0
        seeding_time_limit_met = seeding_time >= seeding_time_limit > 0

        return ratio_limit_met or seeding_time_limit_met

    def _meets_target_criteria(
        self,
        item: dict,
        target_tags: list,
        target_categories: list,
    ) -> bool:
        """Check if an item has the required tags or categories for removal."""
        item_category = item.get("category", "")
        if item_category in target_categories:
            return True

        tags = item.get("tags", "").split(",")
        item_tags = {tag.strip() for tag in tags if tag.strip()}

        return bool(item_tags.intersection(target_tags))

    def _get_targets(self) -> tuple[list, list]:
        """Get the list of tags and categories to look for from job settings."""
        tags = getattr(self.job, "target_tags", [])
        categories = getattr(self.job, "target_categories", [])
        return tags, categories
