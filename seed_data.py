"""
Seed script for initial demo data.
Run once to populate the database with a sample policy template and widget config.
Tables are created automatically on app startup — this only needs to create demo data.
"""
import asyncio
import json
from app.infrastructure.database import engine, AsyncSessionLocal
from app.modules.policies.models import Base, PolicyTemplate, ClientWidget
from sqlalchemy import select


async def seed():
    if not engine:
        print("ERROR: Database engine not initialized. Check DATABASE_URL.")
        return

    # Ensure tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if data already exists
        result = await session.execute(
            select(ClientWidget).where(ClientWidget.id == "demo-client-123")
        )
        if result.scalar_one_or_none():
            print("Demo data already exists. Skipping seed.")
            return

        # Create Template
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
            version=1,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)

        # Create Widget Config for Demo Client
        widget = ClientWidget(
            id="demo-client-123",
            domain="localhost",
            policy_template_id=template.id,
            config_json=json.dumps({
                "company_name": "Demo Corp Ltd.",
                "date": "2026-02-12",
                "contact_email": "privacy@demo.com",
                "retention_years": 3,
            }),
        )
        session.add(widget)
        await session.commit()

        print("Database seeded successfully!")
        print("Demo Widget ID: demo-client-123")


if __name__ == "__main__":
    asyncio.run(seed())
