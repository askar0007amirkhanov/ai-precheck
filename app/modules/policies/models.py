from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PolicyTemplateMaster(Base):
    """Master policy templates managed by admin. Versioned for approach B."""
    __tablename__ = "policy_templates_master"

    id = Column(Integer, primary_key=True, index=True)
    policy_type = Column(String, nullable=False, index=True)  # privacy, terms, refund, cancellation, payment
    jurisdiction = Column(String, default="GENERAL")  # EU, CY, UK, US, GENERAL
    language = Column(String, default="en")
    prompt_template = Column(Text, nullable=False)  # Gemini prompt for generation
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ClientPolicy(Base):
    """Generated policy for a specific client."""
    __tablename__ = "client_policies"

    id = Column(String, primary_key=True)  # pol_uuid
    client_id = Column(String, nullable=False, index=True)
    policy_type = Column(String, nullable=False)  # privacy, terms, refund, cancellation, payment
    master_template_id = Column(Integer, ForeignKey("policy_templates_master.id"), nullable=True)
    master_version_used = Column(Integer, default=1)
    content_html = Column(Text, nullable=False)
    jurisdiction = Column(String, default="GENERAL")
    language = Column(String, default="en")
    version = Column(Integer, default=1)
    status = Column(String, default="draft")  # draft, approved, outdated
    created_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)

    master_template = relationship("PolicyTemplateMaster", foreign_keys=[master_template_id])


class ComplianceReportRecord(Base):
    """Stored compliance report for rate limiting and history."""
    __tablename__ = "compliance_reports"

    id = Column(String, primary_key=True)  # rpt_uuid
    client_id = Column(String, nullable=True, index=True)  # null for web form checks
    site_url = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # COMPLIANT, NON-COMPLIANT, NEEDS_REVIEW
    checklist = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Widget(Base):
    """Widget config for serving policies on merchant sites."""
    __tablename__ = "widgets"

    token = Column(String, primary_key=True)  # wt_pub_uuid
    client_id = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    theme_config = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
