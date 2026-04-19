import asyncio
import os
import time

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.config_manager import ConfigManager
from src.web.database import ActivityRecorder, Database
from src.web.events import EventBus, EventType
from src.web.routes import api_router, page_router


def create_app(settings, event_bus: EventBus, trigger_event: asyncio.Event = None) -> FastAPI:
    app = FastAPI(title="Decluttarr", docs_url="/api/docs", redoc_url=None)

    # Static files and templates
    web_dir = os.path.dirname(__file__)
    app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

    templates = Jinja2Templates(directory=os.path.join(web_dir, "templates"))

    # Store shared state
    app.state.settings = settings
    app.state.event_bus = event_bus
    app.state.templates = templates
    app.state.start_time = time.time()
    app.state.trigger_event = trigger_event
    app.state.first_cycle_done = False

    # Register routes
    app.include_router(api_router)
    app.include_router(page_router)

    return app


async def start_web_server(settings, event_bus: EventBus, trigger_event: asyncio.Event = None):
    """Start the web server as an async task."""
    from src.utils.log_setup import logger

    # Initialize database
    database = Database()
    await database.init()

    host = settings.web.host
    port = settings.web.port
    proxy_prefix = getattr(settings.web, "proxy_prefix", None)
    root_path = f"/{proxy_prefix}/{port}" if proxy_prefix else ""

    # Create app
    app = create_app(settings, event_bus, trigger_event)
    app.state.database = database

    # Config manager
    config_manager = ConfigManager(database, settings)
    await config_manager.apply_all_overrides()
    app.state.config_manager = config_manager

    # Start activity recorder
    recorder = ActivityRecorder(database, event_bus)
    await recorder.start()
    app.state.recorder = recorder

    # Track when the first main-loop cycle finishes so partials can show
    # a "waiting" message instead of hanging on arr API calls during startup.
    async def _mark_first_cycle_done():
        queue = event_bus.subscribe()
        try:
            while True:
                event = await queue.get()
                if event.event_type == EventType.CYCLE_END:
                    app.state.first_cycle_done = True
                    break
        finally:
            event_bus.unsubscribe(queue)

    asyncio.create_task(_mark_first_cycle_done())

    # Schedule daily cleanup of old activity log entries
    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(86400)  # 24 hours
            try:
                deleted = await database.cleanup_old_activity(days=90)
                if deleted:
                    logger.info(f"Activity log cleanup: removed {deleted} entries older than 90 days")
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Activity log cleanup error: {e}")

    asyncio.create_task(_periodic_cleanup())

    # Run initial cleanup on startup
    try:
        deleted = await database.cleanup_old_activity(days=90)
        if deleted:
            logger.info(f"Activity log cleanup: removed {deleted} entries older than 90 days")
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Activity log cleanup error: {e}")

    logger.info(f"Web UI starting on http://{host}:{port}")
    if proxy_prefix:
       logger.debug(f"Web UI root path:{root_path}") 

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="debug",
        access_log=False,
        root_path=root_path,
    )
    server = uvicorn.Server(config)
    await server.serve()