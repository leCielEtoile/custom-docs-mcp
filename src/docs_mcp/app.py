from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP

from .config import Config
from .db import Database
from .embeddings import create_provider
from .fetcher import run_ingestion
from .server import create_server

logger = logging.getLogger(__name__)


def build_app(config: Config) -> FastMCP:
    provider = create_provider(config.embedding)
    db = Database(config.resolved_db_path(), provider.dimension)

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_ingestion,
        CronTrigger.from_crontab(config.schedule),
        args=[config, db, provider],
        id="periodic_ingestion",
        max_instances=1,
    )

    @asynccontextmanager
    async def lifespan(_app: object) -> AsyncIterator[None]:
        scheduler.start()
        ingestion_task = asyncio.create_task(
            run_ingestion(config, db, provider),
            name="initial_ingestion",
        )
        ingestion_task.add_done_callback(
            lambda t: logger.error("Initial ingestion failed: %s", t.exception())
            if t.exception() else None
        )
        try:
            yield
        finally:
            scheduler.shutdown(wait=False)
            ingestion_task.cancel()

    return create_server(config, db, provider, lifespan=lifespan)
