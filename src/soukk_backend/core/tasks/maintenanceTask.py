import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from soukk_backend.core.celeryApp import celery_app
from soukk_backend.domains.auth import authRepository
from soukk_backend.settings.maintenanceSettings import maintenance_settings

logger = logging.getLogger(__name__)


async def cleanup_refresh_tokens(database_url: str, batch_size: int) -> int:
    """Delete every expired refresh token in batches; returns the total deleted.

    Each batch is its own short transaction, so a big backlog never locks the
    table for long or builds one huge transaction.
    """
    # A fresh engine without a pool: each job runs in its own asyncio.run event
    # loop, and pooled connections can't be reused across event loops.
    engine = create_async_engine(database_url, poolclass=NullPool)
    total = 0
    try:
        async with AsyncSession(engine) as db:
            while True:
                deleted = await authRepository.delete_expired_refresh_tokens(db, batch_size)
                await db.commit()
                total += deleted
                if deleted < batch_size:
                    return total
    finally:
        await engine.dispose()


@celery_app.task
def cleanup_refresh_tokens_task() -> None:
    deleted = asyncio.run(
        cleanup_refresh_tokens(
            maintenance_settings.database_url, maintenance_settings.token_cleanup_batch_size
        )
    )
    logger.info("Deleted %d expired refresh tokens", deleted)
