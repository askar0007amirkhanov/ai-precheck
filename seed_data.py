import asyncio
import json
from app.infrastructure.database import engine, AsyncSessionLocal
from app.modules.policies.models import Base, PolicyTemplate, ClientWidget

async def seed():
    print("Creating tables...")
    # 1. Init DB Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("Seeding data...")
    async with AsyncSessionLocal() as session:
        # 2. Create Template
        template = PolicyTemplate(
            slug="privacy-v1",
            name="Standard Privacy Policy",
            content_template="""
            <h2>Privacy Policy for {{ company_name }}</h2>
            <p>Effective Date: {{ date }}</p>
            <p>We value your privacy. This policy describes how {{ company_name }} collects data.</p>
            <ul>
                <li>Data Controller: {{ contact_email }}</li>
                <li>Data Retention: {{ retention_years }} years</li>
            </ul>
            <p>Contact us at <a href="mailto:{{ contact_email }}">{{ contact_email }}</a>.</p>
            """,
            version=1
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # 3. Create Widget Config for Demo Client
        widget = ClientWidget(
            id="demo-client-123", # Fixed ID for demo
            domain="localhost",
            policy_template_id=template.id,
            config_json=json.dumps({
                "company_name": "Demo Corp Ltd.",
                "date": "2026-02-12",
                "contact_email": "privacy@demo.com",
                "retention_years": 3
            })
        )
        session.add(widget)
        await session.commit()
        
        print("Database seeded successfully!")
        print("Demo Widget ID: demo-client-123")

if __name__ == "__main__":
    asyncio.run(seed())
