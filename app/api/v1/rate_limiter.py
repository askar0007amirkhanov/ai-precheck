"""Rate limiter: 1 compliance check per client per day."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


async def check_rate_limit(client_id: str, db: AsyncSession) -> None:
    """
    Check if the client has already performed a compliance check today.
    Raises 429 if limit exceeded.
    """
    from app.modules.policies.models import ComplianceReportRecord

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    stmt = (
        select(func.count())
        .select_from(ComplianceReportRecord)
        .where(
            ComplianceReportRecord.client_id == client_id,
            ComplianceReportRecord.created_at >= today_start,
        )
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0

    if count >= 1:
        logger.info("Rate limit exceeded for client %s (count=%d)", client_id, count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit: 1 compliance check per client per day. Try again tomorrow.",
        )
