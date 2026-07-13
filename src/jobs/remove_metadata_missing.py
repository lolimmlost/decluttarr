from src.jobs.removal_job import RemovalJob


class RemoveMetadataMissing(RemovalJob):
    queue_scope = "normal"
    blocklist = True

    async def _find_affected_items(self):
        # qBittorrent surfaces a dedicated *arr error message while fetching metadata.
        conditions = [("queued", "qBittorrent is downloading metadata")]
        affected_items = self.queue_manager.filter_queue(self.queue, conditions)

        # Other clients (e.g. Transmission, Deluge) do not surface such a message, so a
        # torrent stuck fetching metadata is invisible to the message-based check above
        # (see #57). Opt-in fallback: also flag queued items whose size is not yet known
        # (size == 0), which is the client-agnostic signature of "no metadata yet".
        # Debounced by max_strikes like the rest of this job.
        if getattr(self.job, "detect_via_missing_size", False):
            seen = {id(item) for item in affected_items}
            for item in self.queue_manager.filter_missing_size(self.queue):
                if id(item) not in seen:
                    affected_items.append(item)
                    seen.add(id(item))

        return affected_items
