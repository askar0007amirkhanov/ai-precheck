from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jinja2 import Template
import json
from app.modules.policies.models import PolicyTemplate, ClientWidget
from app.modules.policies.schemas import PolicyTemplateCreate, WidgetResponse

class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(self, data: PolicyTemplateCreate) -> PolicyTemplate:
        template = PolicyTemplate(**data.model_dump())
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_widget_content(self, client_id: str) -> WidgetResponse:
        # Fetch client config and template
        stmt = select(ClientWidget).where(ClientWidget.id == client_id)
        result = await self.db.execute(stmt)
        widget = result.scalar_one_or_none()
        
        if not widget:
            raise ValueError("Widget not found")
            
        template = await self.db.get(PolicyTemplate, widget.policy_template_id)
        
        # Parse config for variable injection
        context = json.loads(widget.config_json)
        
        # Render HTML
        jinja_template = Template(template.content_template)
        html_content = jinja_template.render(**context)
        
        # Generate JSON-LD (simplified example)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": template.name,
            "url": f"https://{widget.domain}/policies/{template.slug}",
            "publisher": {
                "@type": "Organization",
                "name": context.get("company_name", "Organization")
            }
        }
        
        return WidgetResponse(html_content=html_content, json_ld=json_ld)
