from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PolicyTemplate(Base):
    __tablename__ = "policy_templates"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    content_template = Column(Text, nullable=False)  # Jinja2 template content
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ClientWidget(Base):
    __tablename__ = "client_widgets"

    id = Column(String, primary_key=True)  # UUID/ApiKey
    domain = Column(String, nullable=False)
    policy_template_id = Column(Integer, ForeignKey("policy_templates.id"))

    # JSON config for variable injection (e.g., {"company_name": "MyGlobal Corp"})
    config_json = Column(Text, default="{}")

    template = relationship("PolicyTemplate")
    created_at = Column(DateTime, server_default=func.now())
