"""
Legacy Policy Service — kept for backward compatibility with /api/widget/content/{client_id}.
New functionality uses V1 API endpoints and PolicyGenerator.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.modules.policies.models import Widget, ClientPolicy
from app.modules.policies.schemas import WidgetResponse
from app.modules.policies.generator import POLICY_TYPES

logger = logging.getLogger(__name__)


class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_widget_content(self, client_id: str) -> WidgetResponse:
        """Legacy: return widget HTML for a client. Uses new models."""
        # Find widget by client_id
        stmt = select(Widget).where(Widget.client_id == client_id, Widget.is_active == True)
        result = await self.db.execute(stmt)
        widget = result.scalar_one_or_none()

        if not widget:
            raise ValueError("Widget not found")

        # Fetch approved policies
        stmt = select(ClientPolicy).where(
            ClientPolicy.client_id == client_id,
            ClientPolicy.status == "approved",
        )
        result = await self.db.execute(stmt)
        policies = result.scalars().all()

        if not policies:
            raise ValueError("No approved policies found")

        # Build HTML from approved policies
        html_parts = []
        for p in policies:
            name = POLICY_TYPES.get(p.policy_type, p.policy_type)
            html_parts.append(f"<h2>{name}</h2>\n{p.content_html}")

        html_content = "\n<hr>\n".join(html_parts)

        json_ld = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": "Compliance Policies",
            "publisher": {
                "@type": "Organization",
                "name": client_id,
            },
        }

        return WidgetResponse(html_content=html_content, json_ld=json_ld)
