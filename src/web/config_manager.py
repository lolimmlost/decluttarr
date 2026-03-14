import json

from src.web.database import Database


class ConfigManager:
    """Manages runtime config overrides stored in SQLite."""

    def __init__(self, database: Database, settings):
        self.database = database
        self.settings = settings

    async def get_overrides(self) -> dict:
        cursor = await self.database.db.execute("SELECT key, value FROM config_overrides")
        rows = await cursor.fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    async def set_override(self, key: str, value):
        await self.database.db.execute(
            """INSERT INTO config_overrides (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET value=?, updated_at=datetime('now')""",
            (key, json.dumps(value), json.dumps(value)),
        )
        await self.database.db.commit()
        self._apply_override(key, value)

    async def delete_override(self, key: str):
        await self.database.db.execute("DELETE FROM config_overrides WHERE key=?", (key,))
        await self.database.db.commit()

    async def clear_all_overrides(self):
        """Delete all overrides from DB (reset to YAML defaults)."""
        await self.database.db.execute("DELETE FROM config_overrides")
        await self.database.db.commit()

    async def apply_all_overrides(self):
        overrides = await self.get_overrides()
        for key, value in overrides.items():
            self._apply_override(key, value)

    def _apply_override(self, key: str, value):
        """Apply a single override to the live settings object."""
        parts = key.split(".")
        if len(parts) == 2:  # noqa: PLR2004
            section, attr = parts
            if section == "general":
                if hasattr(self.settings.general, attr):
                    setattr(self.settings.general, attr, value)
            elif section == "jobs":
                job = getattr(self.settings.jobs, attr, None)
                if job and isinstance(value, dict):
                    for k, v in value.items():
                        setattr(job, k, v)
                elif job and isinstance(value, bool):
                    job.enabled = value
        elif len(parts) == 3:  # noqa: PLR2004
            section, job_name, attr = parts
            if section == "jobs":
                job = getattr(self.settings.jobs, job_name, None)
                if job:
                    setattr(job, attr, value)

    def get_current_config(self) -> dict:
        """Return current runtime config as a dict."""
        general = {}
        for attr in ("log_level", "test_run", "timer", "ssl_verification",
                      "private_tracker_handling", "public_tracker_handling",
                      "obsolete_tag", "protected_tag"):
            if hasattr(self.settings.general, attr):
                general[attr] = getattr(self.settings.general, attr)

        jobs = {}
        for job_name in dir(self.settings.jobs):
            job = getattr(self.settings.jobs, job_name, None)
            if hasattr(job, "enabled"):
                job_dict = {"enabled": job.enabled}
                for attr in ("max_strikes", "min_speed", "message_patterns",
                             "target_tags", "keep_archives",
                             "max_concurrent_searches", "min_days_between_searches"):
                    if hasattr(job, attr):
                        job_dict[attr] = getattr(job, attr)
                jobs[job_name] = job_dict

        instances = []
        for arr in self.settings.instances:
            instances.append({
                "name": arr.name,
                "arr_type": arr.arr_type,
                "base_url": arr.base_url,
            })

        return {
            "general": general,
            "jobs": jobs,
            "instances": instances,
        }
